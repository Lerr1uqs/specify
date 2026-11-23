"""本地只读 Review 页面：`specify --root example_specs web`。"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable, Iterable
from difflib import unified_diff
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from itertools import groupby
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlencode

from markdown_it import MarkdownIt

from .config import load_config
from .contract import ContractIdentity
from .errors import SpecifyError
from .history import ContractHistory, HistoryRecord
from .index import list_specs
from .merge import apply
from .models import Change, Contract, DeltaDocument, DeltaOperation, SpecDocument
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

    def render(self, query: dict[str, list[str]]) -> tuple[HTTPStatus, str]:
        """按当前 tab 生成导航和详情；未知引用不进入磁盘读取流程。"""

        tab = "change" if "change" in query else "spec"
        entries = self.changes if tab == "change" else self.specs
        selected = query.get(tab, [""])[0] or next(iter(entries), "")
        status = HTTPStatus.OK
        try:
            if selected and selected not in entries:
                status = HTTPStatus.NOT_FOUND
                detail = f'<p class="notice">找不到 {tab}：{escape(selected)}</p>'
            elif not selected:
                detail = f'<p class="notice">当前项目还没有 {"Change" if tab == "change" else "正式 Spec"}。</p>'
            elif tab == "change":
                detail = self.change_detail(self.changes[selected])
            else:
                detail = self.spec_detail(selected, self.specs[selected])
        except READ_ERRORS as error:
            detail = notice(error)

        groups = (
            ((item.status, item.id, item.id) for item in self.changes.values())
            if tab == "change"
            else (
                (ref.split(":", 1)[0], ref, ref.split(":", 1)[1]) for ref in self.specs
            )
        )
        sidebar = "".join(
            f"<h2>{escape(group)}</h2><ul>"
            + "".join(
                f"<li>{link(tab, key, label, key == selected)}</li>"
                for _, key, label in items
            )
            + "</ul>"
            for group, items in groupby(groups, key=lambda item: item[0])
        )
        return (
            status,
            f"""<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Specify · Review</title><link rel="stylesheet" href="/review.css">
<script src="/review.js" defer></script></head>
<body><a class="skip" href="#review">跳到详情</a>
<header><div class="frame"><h1>Specify <small>Review</small></h1>
<p>{escape(self.paths.root.name)} <span class="pill">本地只读</span></p>
<nav aria-label="视图">{link("spec", "", f"正式 Spec ({len(self.specs)})", tab == "spec")}
{link("change", "", f"Changes ({len(self.changes)})", tab == "change")}</nav></div></header>
<div class="frame layout"><nav class="sidebar" aria-label="项目列表">{sidebar}</nav>
<main id="review">{detail}</main></div></body></html>""",
        )

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

        metadata = read_metadata(change)
        change.metadata = metadata
        receipt = metadata.get("sync")
        history_id = receipt.get("historyId") if isinstance(receipt, dict) else None
        # 已同步或归档的 delta 不得以最新正文重放；拒绝项只展示声明。
        if change.status == "rejected":
            mode, label = "rejected", "未采纳 · 仅展示声明，未应用到正式 Spec"
        elif change.status == "archived" or receipt is not None:
            mode, label = "history", "历史差异 · 读取当次同步快照"
        else:
            mode, label = "preview", "未同步 · 以当前正式 Spec 预览，尚未生效"

        impact = metadata.get("specImpact")
        targets = metadata.get("affects")
        if (
            isinstance(impact, dict)
            and impact.get("kind") == "none"
            and targets is None
        ):
            affected = f'<p class="notice">不影响正式 Spec：{escape(str(impact.get("reason", "")))}</p>'
        elif isinstance(targets, list) and targets and impact is None:
            legend = " ".join(
                f'<span class="pill {operation.lower()}">{action}</span>'
                for operation, action in CONTRACT_ACTIONS.items()
            )
            branches = "".join(
                f"<li>{self.target_detail(change, target, mode, history_id)}</li>"
                for target in targets
            )
            # 以 change 为根，右侧按 affects 分出 Spec，再连到各 Contract。
            affected = (
                f'<p class="notice">{label}</p><p class="impact-legend">连线表示：{legend}</p>'
                f'<section class="impact-tree" aria-label="Change 影响树">'
                '<svg class="impact-curves" aria-hidden="true"></svg>'
                f'<div class="impact-source"><strong>Change</strong><code>{escape(change.id)}</code></div>'
                f'<ul class="impact-branches" role="list">{branches}</ul></section>'
            )
        else:
            affected = notice(
                f"{change.path / 'meta-data.yaml'}：预期非空 affects 列表或 specImpact.kind: none。"
            )

        # 说明尚未写完时不遮住已经存在的 delta。
        try:
            context = self.markdown.render(
                (change.path / "change.md").read_text(encoding="utf-8")
            )
        except READ_ERRORS as error:
            context = notice(error)
        reason = metadata.get("rejectedReason")
        rejection = (
            f'<p class="notice">拒绝原因：{escape(str(reason))}</p>' if reason else ""
        )
        return (
            f'<p class="eyebrow">{escape(change.status)} · {escape(change.kind)} · {escape(change.id)}</p>'
            f"<h2>{escape(str(metadata.get('title') or change.id))}</h2>{rejection}"
            f'<details class="card"><summary>变更说明</summary>{context}</details>'
            f"{self.task_progress(change)}<h3>影响的 Spec</h3>{affected}"
        )

    def task_progress(self, change: Change) -> str:
        """从 tasks.md 计算完成度；任务进度不代表已经同步。"""

        try:
            tasks = parse_tasks_file(change.path / "tasks.md")
        except READ_ERRORS as error:
            # 缺失或无效不等于零进度，也不应挡住下方的影响树。
            return f'<section class="card"><strong>任务进度不可用</strong>{notice(error)}</section>'

        done = sum(task.done for task in tasks)
        total = len(tasks)
        percent = done * 100 // total
        rows = "".join(
            f'<li><span class="pill{" added" if task.done else ""}">'
            f"{'已完成' if task.done else '待完成'}</span> "
            f"<code>{escape(task.number)}</code> {escape(task.text)}</li>"
            for task in tasks
        )
        return (
            '<details class="card task-progress"><summary><strong>任务进度</strong> '
            f'<span class="task-count">已完成 {done} / {total} · {percent}%</span>'
            f'<progress aria-label="任务完成进度" value="{done}" max="{total}">{percent}%</progress>'
            f'</summary><ul class="task-list">{rows}</ul></details>'
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
            preview = None
            warning = ""
            if mode == "preview":
                try:
                    preview = self.preview(reference, action, delta)
                except READ_ERRORS as error:
                    warning = notice(error)
            by_id: dict[str, list[DeltaOperation]] = {}
            for item in delta.operations:
                by_id.setdefault(item.contract_id, []).append(item)
            # 同一 Contract 只有一条边；重命名又修改时以修改色连线。
            contracts = "".join(
                f'<li class="{items[-1].operation.lower()}">'
                + self.operation_detail(
                    change, (kind, name, contract_id), items, mode, history_id, preview
                )
                + "</li>"
                for contract_id, items in by_id.items()
            )
            rows = f'<ul class="impact-contracts" role="list">{contracts}</ul>{warning}'
        current = (
            link("spec", reference, "查看当前 Spec") if reference in self.specs else ""
        )
        return (
            f'<section class="target"><div class="impact-node target-node">'
            f'<h4><span class="pill">{SPEC_ACTIONS[action]}</span> '
            f"<code>{escape(reference)}</code></h4>{current}</div>{rows}</section>"
        )

    def preview(
        self, reference: str, action: str, delta: DeltaDocument
    ) -> tuple[dict[str, Contract], dict[str, Contract]]:
        """用和 sync 一样的合并器在内存预览，不补历史、不更新基线。"""

        path = self.specs.get(reference)
        if (path is None) != (action == "create"):
            state = "已存在" if path else "不存在"
            raise SpecifyError(
                f"无法预览：{reference} 当前{state}，不符合 {action} 的前置条件"
            )
        before = parse_spec_file(path) if path else SpecDocument()
        after = apply(before, delta)
        if bool(after.contracts) == (action == "remove"):
            raise SpecifyError(f"无法预览：{reference} 的 delta 结果与 {action} 不一致")
        return (
            {item.id: item for item in before.contracts},
            {item.id: item for item in after.contracts},
        )

    def operation_detail(
        self,
        change: Change,
        reference: tuple[str, str, str],
        items: list[DeltaOperation],
        mode: str,
        history_id: object,
        preview: tuple[dict[str, Contract], dict[str, Contract]] | None,
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
        if preview is not None:
            before, after = (side.get(contract_id) for side in preview)
            diff = line_diff(contract_lines(before), contract_lines(after))
            if before is not None:
                baselines = change.metadata.get("baseVersions")
                digest = baselines.get(ref) if isinstance(baselines, dict) else None
                if digest != ContractIdentity.body_hash(before.body):
                    explanation = "正文基线已变化" if digest else "尚未捕获正文基线"
                    note = notice(
                        f"{explanation}：{ref}。以下仅按当前正文预览，不代表可以同步。"
                    )
        elif mode == "history" and history_id:
            try:
                records = self.history.read(reference)
            except READ_ERRORS as error:
                note = notice(error)
            else:
                for index, record in enumerate(records):
                    # 自动回填可能共用本次回执，但它是变更前状态，不是同步结果。
                    if (
                        record["source"] == "sync"
                        and record["changeId"] == change.id
                        and record["historyId"] == history_id
                    ):
                        previous = records[index - 1] if index else None
                        if previous is not None or record["action"] == "add":
                            diff = line_diff(
                                history_lines(previous), history_lines(record)
                            )
                        break

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
        return (
            f'<details class="operation"><summary>{badges} <strong>{escape(items[0].title)}</strong> '
            f"<code>{escape(contract_id)}</code></summary>{note}{diff or ''}{declared}</details>"
        )


def link(tab: str, key: str, label: str, selected: bool = False) -> str:
    """生成仅指向站内的链接，并标记当前导航项。"""

    current = ' aria-current="page"' if selected else ""
    return f'<a href="/?{urlencode({tab: key})}"{current}>{escape(label)}</a>'


def notice(value: object) -> str:
    """以纯文本显示诊断，保留出错值和文件位置。"""

    return f'<p class="notice">{escape(str(value))}</p>'


def contract_lines(contract: Contract | None) -> list[str]:
    """保留标题与正文行；不存在的 Contract 对应空文件。"""

    return [f"## {contract.title}", "", *contract.body.split("\n")] if contract else []


def history_lines(record: HistoryRecord | None) -> list[str]:
    """把历史删除状态转换成空文件，便于比较重新新增的 Contract。"""

    if record is None or record["action"] == "remove":
        return []
    return contract_lines(Contract("", record["title"], record["content"]))


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
                    status, body = ReviewPage(paths).render(
                        parse_qs(query, keep_blank_values=True)
                    )
                except READ_ERRORS as error:
                    status, body = HTTPStatus.INTERNAL_SERVER_ERROR, str(error)
                    self.respond(status, body, "text/plain")
                    return
                self.respond(status, body, "text/html")
            elif route in static:
                self.respond(HTTPStatus.OK, *static[route])
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

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
                "default-src 'none'; style-src 'self'; script-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
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
