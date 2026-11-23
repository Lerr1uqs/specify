"""本地只读 Review 页面：`specify --root example_specs web`。"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable, Iterable
from datetime import datetime
from difflib import unified_diff
from hashlib import sha256
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from itertools import groupby
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlencode

from markdown_it import MarkdownIt

from .archive import ArchiveService
from .config import load_config
from .contract import ContractIdentity
from .errors import SpecifyError
from .history import ContractHistory, ContractRef, HistoryRecord
from .index import list_specs
from .merge import apply
from .models import (
    CHANGE_PRIORITIES,
    Change,
    Contract,
    DeltaDocument,
    DeltaOperation,
    SpecDocument,
)
from .parse.delta import parse_delta_file
from .parse.spec import parse_spec_file
from .parse.tasks import parse_tasks_file
from .paths import RepoPaths, scan_changes, validate_id
from .spec_metadata import SpecMetadata
from .validate.changes import read_metadata

SPEC_ACTIONS = {"create": "新增 Spec", "modify": "修改 Spec", "remove": "删除 Spec"}
CONTRACT_ACTIONS = {
    "ADDED": "新增",
    "MODIFIED": "修改",
    "REMOVED": "删除",
    "RENAMED": "重命名",
}
READ_ERRORS = (OSError, UnicodeError, SpecifyError)


class ReviewPage:
    """每次导航读取当前项目，使用原生链接和折叠控件，不写任何文件。"""

    def __init__(self, paths: RepoPaths):
        """复用 CLI 的目录发现规则，避免 Web 将任意 URL 映射为文件。"""

        self.paths = paths
        self.config = load_config(paths)
        self.specs = {
            f"{kind}:{name}": paths.specs / kind / name / "spec.md"
            for kind, name in list_specs(paths, self.config)
        }
        self.changes = {change.id: change for change in scan_changes(paths)}
        self.history = ContractHistory(paths)
        # 不执行项目文档中的 HTML，也不自动加载外部图片。
        self.markdown = MarkdownIt("commonmark", {"html": False}).disable("image")

    def render(
        self, query: dict[str, list[str]], revision: str = ""
    ) -> tuple[HTTPStatus, str]:
        """按当前 tab 生成导航和详情；未知引用不进入磁盘读取流程。"""

        tab = "change" if "change" in query else "spec"
        cutoff = ""
        filter_control = ""
        if tab == "change":
            cutoff = query.get("priority", [""])[0]
            if cutoff not in CHANGE_PRIORITIES:
                cutoff = ""
            entries = self.change_entries(cutoff)
            groups = (
                (item.status, item.id, item.id, item.priority)
                for item in entries.values()
            )
        else:
            entries = self.specs
            groups = (
                (ref.split(":", 1)[0], ref, ref.split(":", 1)[1], None)
                for ref in entries
            )

        # 当前 change 被筛掉时选中首条匹配项，未知 ID 仍按原规则报错。
        selected = query.get(tab, [""])[0]
        if tab == "change" and selected in self.changes and selected not in entries:
            selected = ""
        selected = selected or next(iter(entries), "")
        if tab == "change":
            filter_control = priority_filter(cutoff, selected)
        status = HTTPStatus.OK
        try:
            if selected and selected not in entries:
                status = HTTPStatus.NOT_FOUND
                detail = f'<p class="notice">找不到 {tab}：{escape(selected)}</p>'
            elif not selected:
                if cutoff:
                    detail = notice("没有符合此优先级筛选的 Change。")
                else:
                    detail = f'<p class="notice">当前项目还没有 {"Change" if tab == "change" else "正式 Spec"}。</p>'
            elif tab == "change":
                detail = self.change_detail(self.changes[selected])
            else:
                detail = self.spec_detail(selected, self.specs[selected])
        except READ_ERRORS as error:
            detail = notice(error)

        sidebar = filter_control + "".join(
            f"<h2>{escape(group)}</h2><ul>"
            + "".join(
                f"<li>{link(tab, key, label, key == selected, priority, cutoff)}</li>"
                for _, key, label, priority in items
            )
            + "</ul>"
            for group, items in groupby(groups, key=lambda item: item[0])
        )
        return (
            status,
            f"""<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="specify-revision" content="{escape(revision)}">
<title>Specify · Review</title><link rel="stylesheet" href="/review.css">
<script src="/review.js" defer></script></head>
<body><a class="skip" href="#review">跳到详情</a>
<header><div class="frame"><h1>Specify <small>Review</small></h1>
<p>{escape(self.paths.root.name)} <span class="pill">本地只读</span></p>
<nav aria-label="视图">{link("spec", "", f"正式 Spec ({len(self.specs)})", tab == "spec")}
{link("change", "", f"Changes ({len(self.changes)})", tab == "change", cutoff=cutoff)}</nav></div></header>
<div class="frame layout"><nav class="sidebar" aria-label="项目列表">{sidebar}</nav>
<main id="review">{detail}</main></div></body></html>""",
        )

    def change_entries(self, cutoff: str) -> dict[str, Change]:
        """按状态分组和优先级输出可见 change，同级沿用原扫描顺序。"""

        rank = CHANGE_PRIORITIES.index
        max_rank = rank(cutoff) if cutoff else len(CHANGE_PRIORITIES) - 1
        entries: dict[str, Change] = {}
        for _, changes in groupby(self.changes.values(), key=lambda item: item.status):
            group = list(changes)
            for change in group:
                try:
                    change.metadata = read_metadata(change)
                except READ_ERRORS:
                    # 保留坏草稿的导航入口，选中后由详情展示实际错误。
                    change.metadata = {}
            for change in sorted(group, key=lambda item: rank(item.priority)):
                if rank(change.priority) <= max_rank:
                    entries[change.id] = change
        return entries

    def spec_detail(self, reference: str, path: Path) -> str:
        """渲染当前 Spec 的简介和每条 Contract 的正文。"""

        spec = parse_spec_file(path)
        description = SpecMetadata(path).description() or ""
        cards = "".join(
            f'<section class="card"><code>{escape(contract.id)}</code><h3>{escape(contract.title)}</h3>'
            f"{self.markdown.render(contract.body)}</section>"
            for contract in spec.contracts
        )
        return (
            f'<p class="eyebrow">当前正式 Spec · {len(spec.contracts)} 条 Contract</p>'
            f"<h2>{escape(reference)}</h2><p>{escape(description)}</p>{cards}"
        )

    def change_detail(self, change: Change) -> str:
        """读取 change 说明、生命周期及声明的每个目标 Spec。"""

        metadata = change.metadata or read_metadata(change)
        change.metadata = metadata
        title = str(metadata.get("title") or change.id)
        header = (
            f'<p class="eyebrow">{escape(change.status)} · {escape(change.kind)} · {escape(change.id)}</p>'
            f"<h2>{escape(title)}</h2>"
        )
        try:
            source = (change.path / "change.md").read_text(encoding="utf-8")
            env: dict[str, object] = {}
            tokens = self.markdown.parse(source, env)
            # 总览已经展示名称，省略说明中完全相同的首个一级标题。
            if (
                change.status != "proposed"
                and len(tokens) >= 3
                and tokens[0].tag == "h1"
                and tokens[1].content.strip() == title
            ):
                tokens = tokens[3:]
            context = self.markdown.renderer.render(tokens, self.markdown.options, env)
        except READ_ERRORS as error:
            context = notice(error)

        # 需求录入只展示正文。实施准备之后才出现任务、影响树和差异。
        if change.status == "proposed":
            return (
                f'{header}<section class="card proposal-document" tabindex="0" '
                f'aria-label="需求正文">{context}</section>'
            )

        receipt = metadata.get("sync")
        history_id = receipt.get("historyId") if isinstance(receipt, dict) else None
        # 已同步或归档的 delta 不得以最新正文重放；拒绝项只展示声明。
        if change.status == "rejected":
            mode, label = "rejected", "未采纳 · 仅展示声明，未应用到正式 Spec"
        elif change.status == "archived" or receipt is not None:
            mode, label = "history", "历史差异 · 读取当次同步快照"
        else:
            mode, label = "preview", "未同步 · 按捕获的 Contract 基线预览，尚未生效"

        impact = metadata.get("specImpact")
        targets = metadata.get("affects")
        if (
            isinstance(impact, dict)
            and impact.get("kind") == "none"
            and targets is None
        ):
            affected = f'<p class="notice">不影响正式 Spec：{escape(str(impact.get("reason", "")))}</p>'
        elif isinstance(targets, list) and targets and impact is None:
            branches = "".join(
                f"<li>{self.target_detail(change, target, mode, history_id)}</li>"
                for target in targets
            )
            # 以 change 为根，右侧按 affects 分出 Spec，再连到各 Contract。
            affected = (
                f'<div class="impact-toolbar"><p class="review-mode">{label}</p>'
                '<button type="button" class="impact-toggle" data-toggle-diffs hidden>展开全部</button></div>'
                f'<section class="impact-tree" aria-label="Change 影响树">'
                '<svg class="impact-curves" aria-hidden="true"></svg>'
                f'<div class="impact-source"><strong>Change</strong><code>{escape(change.id)}</code></div>'
                f'<ul class="impact-branches" role="list">{branches}</ul>'
                '<aside id="current-spec-panel" class="spec-inspector" aria-label="当前 Spec" hidden>'
                '<button type="button" class="spec-inspector-close" aria-label="收起 Spec" '
                'title="收起 Spec" data-close-spec><span aria-hidden="true"></span></button>'
                "<div data-spec-content></div></aside></section>"
            )
        elif change.status == "processing" and targets is None and impact is None:
            affected = notice("尚未声明对正式 Spec 的影响。")
        elif change.status == "rejected" and targets is None and impact is None:
            affected = ""
        else:
            affected = notice(
                f"{change.path / 'meta-data.yaml'}：预期非空 affects 列表或 specImpact.kind: none。"
            )

        reason = metadata.get("rejectedReason")
        rejection = (
            f'<p class="notice">拒绝原因：{escape(str(reason))}</p>' if reason else ""
        )
        tasks = self.task_progress(change) if affected else ""
        return (
            f"{header}{self.change_dates(change)}{rejection}"
            f'<div class="change-overview{" with-tasks" if tasks else ""}">'
            '<section class="change-description"><h3>变更说明</h3>'
            f'<div class="description-body">{context}</div></section>{tasks}</div>'
            + (
                f'<section class="change-impact"><h3>影响的 Spec</h3>{affected}</section>'
                if affected
                else ""
            )
        )

    def change_dates(self, change: Change) -> str:
        """用元数据和回执渲染已有的时间，保留记录的时区。"""

        metadata = change.metadata
        receipt = metadata.get("sync")
        dates = [
            ("创建", metadata.get("createdAt")),
            ("更新", metadata.get("updatedAt")),
            ("同步", receipt.get("appliedAt") if isinstance(receipt, dict) else None),
        ]
        warning = ""
        if change.status == "archived":
            try:
                dates.append(("归档", ArchiveService(self.paths).archived_at(change)))
            except READ_ERRORS as error:
                # 清单读取失败时保留其余时间和 change 内容。
                warning = notice(error)

        rows = []
        for label, value in dates:
            # YAML 时间戳既可能是 datetime，也可能是加引号的字符串。
            if isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value)
                except ValueError:
                    continue
            if isinstance(value, datetime) and value.utcoffset() is not None:
                timestamp = value.isoformat(timespec="seconds")
                rows.append(
                    f'<div><dt>{label}</dt><dd><time datetime="{timestamp}">'
                    f"{value:%Y-%m-%d %H:%M:%S} <span>{timestamp[19:]}</span></time></dd></div>"
                )
        metadata_html = f'<dl class="change-dates">{"".join(rows)}</dl>' if rows else ""
        return metadata_html + warning

    def task_progress(self, change: Change) -> str:
        """从 tasks.md 计算完成度；任务进度不代表已经同步。"""

        try:
            tasks = parse_tasks_file(change.path / "tasks.md")
        except READ_ERRORS as error:
            # 缺失或无效不等于零进度，也不应挡住下方的影响树。
            return f'<section class="task-progress"><h3>任务进度不可用</h3>{notice(error)}</section>'

        done = sum(task.done for task in tasks)
        total = len(tasks)
        percent = done * 100 // total
        rows = "".join(
            f'<li><span class="task-state{" complete" if task.done else ""}">'
            f"{'已完成' if task.done else '待完成'}</span> "
            f"<span><code>{escape(task.number)}</code> {escape(task.text)}</span></li>"
            for task in tasks
        )
        return (
            '<section class="task-progress"><div class="task-heading"><h3>任务进度</h3>'
            f'<span class="task-count">已完成 {done} / {total} · {percent}%</span></div>'
            f'<progress aria-label="任务完成进度" value="{done}" max="{total}">{percent}%</progress>'
            f'<ul class="task-list">{rows}</ul></section>'
        )

    def target_detail(
        self, change: Change, target: object, mode: str, history_id: object
    ) -> str:
        """验证目录段，按目标渲染 Contract 操作；单个坏草稿不遮住别的目标。"""

        if not isinstance(target, dict):
            return notice(f"affects 项必须是映射，当前值：{target!r}")
        kind, name, action = target.get("type"), target.get("id"), target.get("change")
        if not (
            isinstance(kind, str)
            and kind in self.config["specTypes"]
            and isinstance(name, str)
            and validate_id(name)
            and isinstance(action, str)
            and action in SPEC_ACTIONS
        ):
            return notice(
                f"affects 项必须使用已配置类型、kebab-case ID 和 create/modify/remove，当前值：{target!r}"
            )

        reference = f"{kind}:{name}"
        path = change.path / "deltas" / kind / f"{name}.md"
        try:
            delta = parse_delta_file(path)
        except READ_ERRORS as error:
            rows = notice(error)
        else:
            current_contracts: dict[str, Contract] | None = {}
            warning = ""
            current_path = self.specs.get(reference)
            try:
                if current_path is not None and mode != "rejected":
                    current_contracts = {
                        item.id: item
                        for item in parse_spec_file(current_path).contracts
                    }
            except READ_ERRORS as error:
                current_contracts = None
                warning = notice(error)
            by_id: dict[str, list[DeltaOperation]] = {}
            for item in delta.operations:
                by_id.setdefault(item.contract_id, []).append(item)
            # 同一 Contract 只有一条边；重命名又修改时以修改色连线。
            contracts = "".join(
                f'<li class="{items[-1].operation.lower()}">'
                + self.operation_detail(
                    change,
                    (kind, name, contract_id),
                    items,
                    mode,
                    history_id,
                    current_contracts,
                )
                + "</li>"
                for contract_id, items in by_id.items()
            )
            rows = f'<ul class="impact-contracts" role="list">{contracts}</ul>{warning}'
        heading = (
            f'<span class="pill">{SPEC_ACTIONS[action]}</span> '
            f"<code>{escape(reference)}</code>"
        )
        current = reference in self.specs
        if current:
            url = escape(urlencode({"spec": reference}))
            heading = (
                f'<a class="target-current" href="/?{url}" aria-controls="current-spec-panel" '
                f'aria-expanded="false" data-open-spec>{heading}'
                '<span class="target-arrow" aria-hidden="true"></span></a>'
            )
        return (
            f'<section class="target"><div class="impact-node target-node{" has-current" if current else ""}">'
            f"<h4>{heading}</h4></div>{rows}</section>"
        )

    def operation_detail(
        self,
        change: Change,
        reference: ContractRef,
        items: list[DeltaOperation],
        mode: str,
        history_id: object,
        current_contracts: dict[str, Contract] | None,
    ) -> str:
        """合并同一 Contract 的重命名和修改，用一份 diff 展示净变化。"""

        contract_id = reference[-1]
        ref = ":".join(reference)
        badges = " ".join(
            f'<span class="pill {item.operation.lower()}">{CONTRACT_ACTIONS[item.operation]}</span>'
            for item in items
        )
        diff: str | None = None
        note = ""
        stale = False
        current = (current_contracts or {}).get(contract_id)
        baselines = change.metadata.get("baseVersions")
        digest = baselines.get(ref) if isinstance(baselines, dict) else None
        try:
            if mode == "preview":
                before = current
                if items[0].operation == "ADDED":
                    before = None
                    stale = current is not None
                elif digest:
                    # 标题用于区分正文相同、但已重命名的历史版本。
                    matches_current = matches_baseline(current, digest, items[0].title)
                    stale = current_contracts is not None and not matches_current
                    if not matches_current:
                        before = find_baseline(
                            self.history.read(reference),
                            contract_id,
                            digest,
                            items[0].title,
                        )
                    if before is None:
                        note = self.current_contract_notice(
                            "找不到与基线 hash 匹配的历史正文", ref, current
                        )
                    elif stale:
                        note = self.current_contract_notice(
                            "正文基线已变化",
                            ref,
                            current,
                            "以下显示基于原始基线的差异。",
                        )
                else:
                    note = notice(
                        f"尚未捕获正文基线：{ref}。有当前正文时按当前正文预览。"
                    )

                # 逐条使用各自的历史基线，避免当前 Spec 中的其他 Contract 干扰草稿 diff。
                if before is not None or items[0].operation == "ADDED":
                    result = apply(
                        SpecDocument([before] if before else []), DeltaDocument(items)
                    )
                    after = next(iter(result.contracts), None)
                    diff = line_diff(contract_lines(before), contract_lines(after))
            elif mode == "history" and history_id:
                records = self.history.read(reference)
                for index, record in enumerate(records):
                    # 自动回填可能共用本次回执，但它是变更前状态，不是同步结果。
                    if (
                        record["source"] == "sync"
                        and record["changeId"] == change.id
                        and record["historyId"] == history_id
                    ):
                        after = history_contract(contract_id, record)
                        stale = current_contracts is not None and after != current
                        before = (
                            history_contract(contract_id, records[index - 1])
                            if index
                            else None
                        )
                        if record["action"] == "add":
                            diff = line_diff([], contract_lines(after))
                        else:
                            # 旧历史可能缺一条紧邻快照，只在本次同步前的记录中按 hash 查找。
                            if digest and not matches_baseline(
                                before, digest, items[0].title
                            ):
                                before = find_baseline(
                                    records[:index], contract_id, digest, items[0].title
                                )
                            if before is not None:
                                diff = line_diff(
                                    contract_lines(before), contract_lines(after)
                                )
                        break
        except READ_ERRORS as error:
            note = notice(error)

        # 没有可信的前后快照时，宁可展示声明，也不用当前正式正文猜测历史。
        if diff is None:
            if mode == "history":
                note += notice(
                    f"没有可还原的当次同步快照：{ref}。下方仅展示 delta 声明。"
                )
            declared = "".join(
                (f"<p>新标题：{escape(item.new_title)}</p>" if item.new_title else "")
                + self.markdown.render(item.body)
                for item in items
            )
        else:
            declared = "".join(
                self.markdown.render(item.body)
                for item in items
                if item.operation == "REMOVED"
            )
        marker = '<span class="pill stale">已落后当前 Spec</span>' if stale else ""
        return (
            f'<details class="operation" data-review-details="{escape(ref)}">'
            f"<summary>{badges} <strong>{escape(items[0].title)}</strong> "
            f"<code>{escape(contract_id)}</code>{marker}</summary>{note}{diff or ''}{declared}</details>"
        )

    def current_contract_notice(
        self, message: str, reference: str, contract: Contract | None, suffix: str = ""
    ) -> str:
        """提示基线问题，并在当前 Contract 存在时提供正文弹窗。"""

        if contract is None:
            return notice(f"{message}：{reference}。{suffix}")

        dialog_id = escape(f"current-{reference}")
        return (
            f'<p class="notice">{escape(message)}：'
            f'<button type="button" class="contract-link" aria-haspopup="dialog" '
            f'aria-controls="{dialog_id}" data-current-contract>{escape(reference)}</button>'
            f"。{escape(suffix)}</p>"
            f'<dialog class="contract-dialog" id="{dialog_id}" aria-labelledby="{dialog_id}-title">'
            '<div class="contract-dialog-header">'
            f'<h3 id="{dialog_id}-title">当前正式 Contract</h3>'
            '<button type="button" class="contract-close" data-close-contract autofocus>关闭</button>'
            "</div>"
            f"<code>{escape(reference)}</code><h4>{escape(contract.title)}</h4>"
            f"{self.markdown.render(contract.body)}</dialog>"
        )


def priority_filter(cutoff: str, change_id: str) -> str:
    """用可分享的站内链接渲染筛选菜单，并标出当前选项。"""

    options = []
    for priority in ("", *CHANGE_PRIORITIES):
        params = {"change": change_id}
        if priority:
            params["priority"] = priority
            badge = f'<span class="priority-badge {priority.lower()}">{priority}</span>'
            label = f"{badge}<span>及以上</span>"
        else:
            label = '<span class="priority-all">全部优先级</span>'
        current = ' aria-current="true"' if priority == cutoff else ""
        url = escape(urlencode(params))
        options.append(
            f'<li><a href="/?{url}"{current}>{label}'
            '<span class="priority-check" aria-hidden="true"></span></a></li>'
        )

    value = f"{cutoff} 及以上" if cutoff else "全部"
    return (
        '<details class="priority-filter" data-priority-filter>'
        '<summary><span class="priority-filter-icon" aria-hidden="true"></span>'
        f'<span>优先级</span><span class="priority-value">{value}</span>'
        '<span class="priority-chevron" aria-hidden="true"></span></summary>'
        f'<ul class="priority-options" aria-label="按优先级筛选">{"".join(options)}</ul></details>'
    )


def link(
    tab: str,
    key: str,
    label: str,
    selected: bool = False,
    priority: str | None = None,
    cutoff: str = "",
) -> str:
    """生成站内链接，保留筛选并为 change 标记优先级。"""

    current = ' aria-current="page"' if selected else ""
    params = {tab: key}
    if cutoff:
        params["priority"] = cutoff
    url = escape(urlencode(params))
    if priority is not None:
        badge = f'<span class="priority-badge {priority.lower()}">{priority}</span>'
        return f'<a class="change-link" href="/?{url}"{current}>{badge}<span>{escape(label)}</span></a>'
    return f'<a href="/?{url}"{current}>{escape(label)}</a>'


def notice(value: object) -> str:
    """以纯文本显示诊断，保留出错值和文件位置。"""

    return f'<p class="notice">{escape(str(value))}</p>'


def contract_lines(contract: Contract | None) -> list[str]:
    """保留标题与正文行；不存在的 Contract 对应空文件。"""

    return [f"## {contract.title}", "", *contract.body.split("\n")] if contract else []


def history_contract(contract_id: str, record: HistoryRecord) -> Contract | None:
    """读取历史快照，删除事件没有现存 Contract。"""

    if record["action"] == "remove":
        return None
    return Contract(contract_id, record["title"], record["content"])


def matches_baseline(contract: Contract | None, digest: object, title: str) -> bool:
    """按正文 hash 精确匹配，并用 delta 旧标题区分重命名。"""

    return (
        contract is not None
        and ContractIdentity.body_hash(contract.body) == digest
        and ContractIdentity.normalize_title(contract.title)
        == ContractIdentity.normalize_title(title)
    )


def find_baseline(
    records: list[HistoryRecord], contract_id: str, digest: object, title: str
) -> Contract | None:
    """从历史中取最近一份与正文 hash 和旧标题一致的快照。"""

    for record in reversed(records):
        snapshot = history_contract(contract_id, record)
        if matches_baseline(snapshot, digest, title):
            return snapshot
    return None


def line_diff(before: Iterable[str], after: Iterable[str]) -> str:
    """以带正负号的逐行差异标记新增、删除与上下文。"""

    lines = list(unified_diff(list(before), list(after), lineterm=""))[2:]
    if not lines:
        return '<p class="notice">标题与正文无差异。</p>'
    colors = {"+": "insert", "-": "delete", "@": "hunk"}
    content = "\n".join(
        f'<span class="{colors.get(line[0], "context")}">{escape(line)}</span>'
        for line in lines
    )
    return f'<pre class="diff" aria-label="逐行差异"><code>{content}</code></pre>'


def project_revision(paths: RepoPaths) -> str:
    """为 Review 读取的 Markdown、元数据和历史文件生成变更标记。"""

    digest = sha256()
    manifest = paths.changes / "archived" / "manifest.json"
    for path in sorted(paths.spec.rglob("*")):
        if path.suffix not in {".md", ".yaml", ".jsonl"} and path != manifest:
            continue
        try:
            info = path.stat()
        except FileNotFoundError:
            # 编辑器可能在扫描与读取属性之间原子替换或移动文件。
            continue
        digest.update(
            f"{path.relative_to(paths.spec)}\0{info.st_mtime_ns}\0{info.st_size}\n".encode()
        )
    return digest.hexdigest()


def serve_review(paths: RepoPaths, announce: Callable[[str], None]) -> None:
    """只监听本机临时端口，打开默认浏览器；Ctrl+C 结束服务。"""

    # 显式列出可访问的打包资源，不从请求路径读取项目文件。
    assets = files("specify").joinpath("assets")
    static = {
        route: (assets.joinpath(route[1:]).read_text(encoding="utf-8"), media_type)
        for route, media_type in {
            "/review.css": "text/css",
            "/review.js": "text/javascript",
        }.items()
    }

    class Handler(BaseHTTPRequestHandler):
        """只提供渲染好的 Review 和打包资源，不提供文件服务器。"""

        def do_GET(self) -> None:
            """拒绝非本地 Host，避免外部站点通过 DNS 重绑定读取项目。"""

            if self.headers.get_all("Host") != [authority]:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            route, _, query = self.path.partition("?")
            if route == "/":
                try:
                    revision = project_revision(paths)
                    status, body = ReviewPage(paths).render(
                        parse_qs(query, keep_blank_values=True), revision
                    )
                except READ_ERRORS as error:
                    status, body = HTTPStatus.INTERNAL_SERVER_ERROR, str(error)
                    self.respond(status, body, "text/plain")
                    return
                self.respond(status, body, "text/html")
            elif route == "/revision":
                self.respond(HTTPStatus.OK, project_revision(paths), "text/plain")
            elif route in static:
                self.respond(HTTPStatus.OK, *static[route])
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
            """定时探测不占据终端日志，正常页面请求照常记录。"""

            if self.path != "/revision" or code != HTTPStatus.OK:
                super().log_request(code, size)

        def respond(self, status: HTTPStatus, body: str, media_type: str) -> None:
            """只允许同源静态资源，禁止内联脚本、跨站嵌入和缓存。"""

            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", f"{media_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'self'; script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(encoded)

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        authority = f"127.0.0.1:{server.server_port}"
        url = f"http://{authority}/"
        announce(url)
        Thread(target=webbrowser.open, args=(url,), daemon=True).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
