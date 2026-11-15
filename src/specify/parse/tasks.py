"""tasks.md 复选框和编号格式解析。"""

from __future__ import annotations

import re
from pathlib import Path

from ..errors import SpecifyError
from ..models import Task

TASK_PATTERN = re.compile(r"^\s*-\s*\[([ xX])\]\s+(\d+(?:\.\d+)*)\s+(.+?)\s*$")


class TaskParser:
    """读取任务文档并检查任务编号唯一性。"""

    def parse(self, source: str, path: str | None = None) -> list[Task]:
        """解析所有 checkbox 项，并指出格式错误的行号。"""

        tasks: list[Task] = []
        seen: set[str] = set()
        for line_number, line in enumerate(source.splitlines(), 1):
            if "[" not in line or "]" not in line:
                continue
            match = TASK_PATTERN.match(line)
            if not match:
                raise SpecifyError(f"第 {line_number} 行的 task 格式无效", path=path)
            state, number, text = match.groups()
            if number in seen:
                raise SpecifyError(f"task 编号重复：{number}", path=path)
            seen.add(number)
            tasks.append(Task(number, text, state.lower() == "x"))

        if not tasks:
            raise SpecifyError("tasks.md 至少需要一个 checkbox task", path=path)
        return tasks

    def parse_file(self, path: Path) -> list[Task]:
        """读取 UTF-8 tasks.md 并调用统一解析逻辑。"""

        return self.parse(path.read_text(encoding="utf-8"), path.as_posix())


_PARSER = TaskParser()


def parse_tasks(source: str, path: str | None = None) -> list[Task]:
    """解析任务 Markdown。"""

    return _PARSER.parse(source, path)


def parse_tasks_file(path: Path) -> list[Task]:
    """读取并解析一个任务文件。"""

    return _PARSER.parse_file(path)
