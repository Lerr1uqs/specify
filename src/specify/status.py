"""只读汇总 formal spec 和 change 的状态，供 JSON 与人类视图共用。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from .config import load_config
from .errors import SpecifyError
from .index import list_specs
from .parse.tasks import parse_tasks_file
from .paths import RepoPaths, scan_changes
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
            issues = [
                issue
                for issue in spec_issues
                if issue.path and Path(issue.path) in {directory, directory / "spec.md"}
            ]
            reference = f"{spec_type}:{spec_id}"
            specs.append(
                {
                    "type": spec_type,
                    "id": spec_id,
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
    """只为显式 --human 选项渲染 Rich 表格。"""

    def __init__(self, console: Console):
        """绑定 stdout 控制台，沿用 Rich 的终端宽度检测。"""

        self.console = console

    def specs(self, items: list[dict[str, Any]]) -> None:
        """展示 formal spec 的类型、ID、校验状态和关联 change 数。"""

        table = Table(title="Formal specs", expand=True)
        for heading in ("Type", "ID", "Status", "Changes"):
            table.add_column(heading, overflow="fold")
        for item in items:
            table.add_row(
                item["type"], item["id"], item["status"], str(len(item["changes"]))
            )
        self.console.print(table)

    def changes(self, items: list[dict[str, Any]]) -> None:
        """展示 change 身份、生命周期、校验结果和任务进度。"""

        table = Table(title="Changes", expand=True)
        for heading in ("ID", "Kind", "State", "Validation", "Tasks"):
            table.add_column(heading, overflow="fold")
        for item in items:
            tasks = item["tasks"]
            table.add_row(
                item["id"],
                item["kind"],
                item["status"],
                item["validation"],
                f"{tasks['done']}/{tasks['total']}" if tasks else "—",
            )
        self.console.print(table)
