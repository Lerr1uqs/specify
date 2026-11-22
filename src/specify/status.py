"""只读汇总 formal spec 和 change 的状态，供 JSON 与人类视图共用。"""

from __future__ import annotations

from itertools import cycle, groupby
from operator import itemgetter
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.text import Text
from rich.tree import Tree

from .config import load_config
from .errors import SpecifyError
from .index import list_specs
from .models import Issue
from .parse.tasks import parse_tasks_file
from .paths import RepoPaths, scan_changes
from .spec_metadata import SpecMetadata
from .validate.changes import validate_change
from .validate.specs import validate_specs


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
            if change.status in {"proposed", "implemented"}:
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
                        if change["status"] in {"proposed", "implemented"}
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
