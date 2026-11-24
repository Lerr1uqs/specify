"""只读汇总 formal spec 和 change 的状态，供 JSON 与人类视图共用。"""

from __future__ import annotations

from itertools import cycle, groupby
from operator import itemgetter
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.text import Text
from rich.tree import Tree

from .archive import ArchiveValidator
from .config import load_config
from .errors import SpecifyError
from .index import list_specs
from .models import Change, Issue
from .parse.tasks import parse_tasks_file
from .paths import RepoPaths, scan_changes, validate_id
from .spec_metadata import SpecMetadata
from .validate.changes import read_metadata, validate_change
from .validate.specs import validate_specs


class ChangeHandoff:
    """汇总单个 change 的证据、阻塞项与下一步，只读取项目文件。"""

    def __init__(self, paths: RepoPaths):
        """绑定路径，文件引用统一相对于项目根。"""

        self.paths = paths

    def read(self, change: Change) -> tuple[dict[str, Any], list[Issue]]:
        """复用生命周期校验，再补充供交接使用的文件和任务信息。"""

        config = load_config(self.paths)
        if change.status == "archived":
            issues = ArchiveValidator(self.paths).validate(change)
            try:
                change.metadata = read_metadata(change)
            except SpecifyError as error:
                issues.append(Issue(error.message, error.path))
        else:
            issues = validate_change(self.paths, config, change)

        metadata = change.metadata
        directory = change.path.relative_to(self.paths.root)
        files: list[dict[str, Any]] = []
        missing: list[dict[str, str]] = []
        roles = {
            "metadata": change.path / "meta-data.yaml",
            "context": change.path / "change.md",
        }
        if change.status == "archived":
            roles["manifest"] = self.paths.changes / "archived" / "manifest.json"
        tasks_path = change.path / "tasks.md"
        if tasks_path.is_file() or change.status in {
            "processing",
            "implemented",
            "archived",
        }:
            roles["tasks"] = tasks_path
        for role, file_path in roles.items():
            path = file_path.relative_to(self.paths.root).as_posix()
            exists = file_path.is_file()
            files.append({"role": role, "path": path, "exists": exists})
            if not exists:
                missing.append({"kind": "file", "path": path})

        # 只用合法的 Spec 引用构造路径。坏的声明由原校验器报告。
        affects = metadata.get("affects")
        references = []
        for target in affects if isinstance(affects, list) else []:
            if not isinstance(target, dict):
                continue
            kind, name = target.get("type"), target.get("id")
            if not isinstance(kind, str) or kind not in config["specTypes"]:
                continue
            if not isinstance(name, str) or not validate_id(name):
                continue
            references.append(f"{kind}:{name}")
            delta = directory / "deltas" / kind / f"{name}.md"
            exists = (self.paths.root / delta).is_file()
            files.append({"role": "delta", "path": delta.as_posix(), "exists": exists})
            if not exists and change.status in {
                "processing",
                "implemented",
                "archived",
            }:
                missing.append({"kind": "file", "path": delta.as_posix()})
            spec = self.paths.specs / kind / name / "spec.md"
            files.append(
                {
                    "role": "spec",
                    "path": spec.relative_to(self.paths.root).as_posix(),
                    "exists": spec.is_file(),
                }
            )

        if (
            change.status == "processing"
            and metadata
            and not {"affects", "specImpact"} & metadata.keys()
        ):
            missing.append({"kind": "spec-impact"})
        for issue in issues:
            if issue.code == "baseline-keys":
                missing.extend(
                    {"kind": "baseline", "reference": reference}
                    for reference in issue.references
                )
        if change.status == "implemented" and references and "sync" not in metadata:
            missing.append({"kind": "sync-receipt"})

        tasks = None
        if tasks_path.is_file():
            try:
                items = parse_tasks_file(tasks_path)
            except SpecifyError:
                # 格式错误由生命周期校验报告，进度保持未知。
                pass
            else:
                pending = [
                    {"id": task.number, "text": task.text}
                    for task in items
                    if not task.done
                ]
                tasks = {
                    "done": len(items) - len(pending),
                    "total": len(items),
                    "pending": pending,
                }

        remaining = len(tasks["pending"]) if tasks else 0
        return {
            "id": change.id,
            "status": change.status,
            "kind": change.kind,
            "priority": change.priority,
            "path": directory.as_posix(),
            "files": files,
            "affects": references,
            "tasks": tasks,
            "missing": missing,
            "nextStep": self._next_step(change, issues, missing, remaining),
        }, issues

    @staticmethod
    def _next_step(
        change: Change,
        issues: list[Issue],
        missing: list[dict[str, str]],
        remaining: int,
    ) -> dict[str, Any] | None:
        """按生命周期和真实校验结果选择下一步，过期基线先审查正文。"""

        if change.status in {"archived", "rejected"}:
            return None
        if issues:
            issue = issues[0]
            if issue.code == "stale-baseline":
                return {
                    "action": "review-stale-baseline",
                    "message": "对照当前 Contract 调整 delta，再重新捕获基线并验证。",
                }
            if issue.code == "baseline-keys" and issue.references:
                return {
                    "action": "capture-baseline",
                    "message": "核对当前 Contract 和 delta 后捕获缺失的基线。",
                    "command": ["specify", "change", "baseline", change.id],
                }
            if not any(item["kind"] == "file" for item in missing) and any(
                item["kind"] == "spec-impact" for item in missing
            ):
                return {
                    "action": "declare-impact",
                    "message": "用 change process 声明 --affect，或用 --no-spec-impact 说明无影响。",
                }
            return {
                "action": "resolve-issues",
                "message": "先处理校验问题，再运行 change verify。",
            }
        if remaining and change.status in {"processing", "implemented"}:
            return {
                "action": "complete-tasks",
                "message": f"完成剩余的 {remaining} 项任务，并核对实现与 Contract。",
            }
        if change.status == "proposed":
            action, message = "process", "确认需求后进入 processing。"
        elif change.status == "processing":
            action, message = "implement", "确认实现后标记为 implemented。"
        elif any(item["kind"] == "sync-receipt" for item in missing):
            action, message = "sync", "将 delta 同步到正式 Spec。"
        else:
            action, message = "archive", "可以归档。"
        return {
            "action": action,
            "message": message,
            "command": ["specify", "change", action, change.id],
        }


class ProjectStatus:
    """从项目文件生成一次查询快照，不修改 spec、change 或索引。"""

    def __init__(self, paths: RepoPaths):
        """保存项目路径，并只在读取时加载配置与文件。"""

        self.paths = paths

    def read(self) -> dict[str, Any]:
        """返回正式 spec、非归档 change 及汇总字段。"""

        config = load_config(self.paths)
        spec_issues = validate_specs(self.paths, config)
        changes: list[dict[str, Any]] = []
        for change in scan_changes(self.paths):
            if change.status == "archived":
                continue
            issues = validate_change(self.paths, config, change)
            metadata = change.metadata
            affects = [
                f"{target['type']}:{target['id']}"
                for target in metadata.get("affects", [])
                if isinstance(target, dict) and "type" in target and "id" in target
            ]
            tasks = None
            if change.status in {"processing", "implemented"}:
                try:
                    parsed = parse_tasks_file(change.path / "tasks.md")
                    tasks = {
                        "done": sum(task.done for task in parsed),
                        "total": len(parsed),
                    }
                except (OSError, SpecifyError):
                    # 校验问题已由 validate_change 报告，进度未知时不猜测数量。
                    pass
            changes.append(
                {
                    "id": change.id,
                    "kind": change.kind,
                    "status": change.status,
                    "priority": change.priority,
                    "validation": "valid" if not issues else "invalid",
                    "tasks": tasks,
                    "affects": affects,
                    "issues": [issue.as_dict() for issue in issues],
                }
            )

        specs: list[dict[str, Any]] = []
        for spec_type, spec_id in list_specs(self.paths, config):
            directory = self.paths.specs / spec_type / spec_id
            spec_path = directory / "spec.md"
            issues = [
                issue
                for issue in spec_issues
                if issue.path and Path(issue.path) in {directory, spec_path}
            ]
            description = None
            try:
                description = SpecMetadata(spec_path).description()
            except SpecifyError as error:
                # 元数据有误时将它标在对应 spec 行，保留其他索引结果。
                issues.append(Issue(error.message, error.path))
            reference = f"{spec_type}:{spec_id}"
            specs.append(
                {
                    "type": spec_type,
                    "id": spec_id,
                    "path": spec_path.relative_to(self.paths.root).as_posix(),
                    "description": description,
                    "status": "valid" if not issues else "invalid",
                    "changes": [
                        change["id"]
                        for change in changes
                        if change["status"] in {"processing", "implemented"}
                        and reference in change["affects"]
                    ],
                    "issues": [issue.as_dict() for issue in issues],
                }
            )
        return {
            "specs": specs,
            "changes": changes,
            "summary": {
                "specs": len(specs),
                "changes": len(changes),
                "invalid": sum(item["status"] == "invalid" for item in specs)
                + sum(item["validation"] == "invalid" for item in changes),
            },
        }


class HumanStatus:
    """为显式 --human 选项渲染 Rich 层级树。"""

    def __init__(self, console: Console):
        """绑定 stdout 控制台，沿用 Rich 的终端宽度检测。"""

        self.console = console

    def specs(self, items: list[dict[str, Any]]) -> None:
        """按 type 建立分支，在子节点展示各 spec 的简介和状态。"""

        tree = Tree(Text("Formal specs", style="bold"), guide_style="dim")
        palette = cycle(("bold cyan", "bold magenta", "bold blue", "bold yellow"))
        # 所有分支共用最长 ID 的宽度，状态从同一列开始。
        status_column = max((len(item["id"]) for item in items), default=0) + 2
        # 项目状态已按 type 和 ID 排序，同一类型只创建一个分支。
        for spec_type, group in groupby(items, key=itemgetter("type")):
            branch = tree.add(Text(spec_type, style=next(palette)))
            for item in group:
                status = item["status"]
                change_count = len(item["changes"])
                change_label = "change" if change_count == 1 else "changes"
                label = Text.assemble(
                    (item["id"], "bold"),
                    " " * (status_column - len(item["id"])),
                    (status, "green" if status == "valid" else "bold red"),
                    (f" · {change_count} {change_label}", "dim"),
                )
                if item["description"]:
                    label.append(f" — {item['description']}")
                branch.add(label)
        self.console.print(tree)

    def changes(self, items: list[dict[str, Any]]) -> None:
        """按状态和 kind 还原目录层级，在 change 旁展示校验与任务进度。"""

        tree = Tree(Text("Changes", style="bold"), guide_style="dim")
        state_styles = {
            "proposed": "bold cyan",
            "processing": "bold blue",
            "implemented": "bold green",
            "rejected": "bold yellow",
        }
        status_column = max((len(item["id"]) for item in items), default=0) + 2
        # change 状态和 kind 继承扫描顺序，同一组内包含各个 change ID。
        for state, changes in groupby(items, key=itemgetter("status")):
            state_branch = tree.add(Text(state, style=state_styles[state]))
            for kind, group in groupby(changes, key=itemgetter("kind")):
                kind_branch = state_branch.add(Text(kind, style="bold magenta"))
                for item in group:
                    status = item["validation"]
                    label = Text.assemble(
                        (item["id"], "bold"),
                        " " * (status_column - len(item["id"])),
                        (status, "green" if status == "valid" else "bold red"),
                    )
                    if tasks := item["tasks"]:
                        label.append(
                            f" · {tasks['done']}/{tasks['total']} tasks", style="dim"
                        )
                    kind_branch.add(label)
        self.console.print(tree)
