"""按显式 Contract ID 解析 delta 操作。"""

from __future__ import annotations

import re
from pathlib import Path

from ..errors import SpecifyError
from ..models import DeltaDocument, DeltaOperation
from .document import MarkdownDocument, MarkdownHeading

OPERATION_HEADING = re.compile(
    r"^\[(ADDED|MODIFIED|REMOVED|RENAMED)\]\s+\[([a-z0-9]+(?:-[a-z0-9]+)*)\]\s+(.+?)$"
)


class DeltaParser:
    """解析协议标题和各操作专属内容。"""

    def parse(self, source: str, path: str | None = None) -> DeltaDocument:
        """校验 delta 外层结构，并按源码顺序解析操作。"""

        document = MarkdownDocument(source, path)
        top_level = [item for item in document.headings if item.level == 1]
        if len(top_level) != 1 or top_level[0].title.lower() != "delta":
            raise SpecifyError("delta must contain only one # delta heading", path=path)
        if document.visible_text("\n".join(document.lines[: top_level[0].start])):
            raise SpecifyError("# delta 前不允许出现正文", path=path)

        operations = [item for item in document.headings if item.level == 2]
        if not operations:
            raise SpecifyError(
                "delta must contain at least one ## operation", path=path
            )
        if document.visible_text(
            document.body_after(top_level[0], operations[0].start)
        ):
            raise SpecifyError(
                "content before the first delta operation is not allowed", path=path
            )

        parsed = [
            self._parse_operation(document, operations, index, path)
            for index in range(len(operations))
        ]
        self._ensure_no_duplicate_operations(parsed, path)
        return DeltaDocument(parsed)

    def _parse_operation(
        self,
        document: MarkdownDocument,
        headings: list[MarkdownHeading],
        index: int,
        path: str | None,
    ) -> DeltaOperation:
        """把一个操作标题和对应正文转成类型化数据。"""

        heading = headings[index]
        match = OPERATION_HEADING.fullmatch(heading.title)
        if not match:
            raise SpecifyError(f"delta 操作标题无效：{heading.title}", path=path)
        operation, contract_id, title_part = match.groups()
        title_part = title_part.strip()
        if not title_part:
            raise SpecifyError(
                f"delta 操作缺少 Contract 标题：[{contract_id}]", path=path
            )
        if operation != "RENAMED" and "->" in title_part:
            raise SpecifyError("Contract 标题不能包含 ->", path=path)
        next_start = headings[index + 1].start if index + 1 < len(headings) else None
        body = document.body_after(heading, next_start)

        if operation == "RENAMED":
            return self._parse_rename(contract_id, title_part, body, path)
        if operation == "REMOVED":
            return self._parse_removal(contract_id, title_part, body, path)
        if not document.visible_text(body):
            raise SpecifyError(
                f"{operation} body must not be empty: [{contract_id}]", path=path
            )
        return DeltaOperation(operation, contract_id, title_part, body)

    def _parse_rename(
        self, contract_id: str, title_part: str, body: str, path: str | None
    ) -> DeltaOperation:
        """要求 RENAMED 只使用一个旧标题/新标题分隔符。"""

        parts = title_part.split(" -> ")
        if len(parts) != 2 or not all(part.strip() for part in parts):
            raise SpecifyError("RENAMED 格式必须为“旧标题 -> 新标题”", path=path)
        if body.strip():
            raise SpecifyError("RENAMED 操作不能包含正文", path=path)
        old_title, new_title = (part.strip() for part in parts)
        if "->" in old_title or "->" in new_title:
            raise SpecifyError("Contract 标题不能包含 ->", path=path)
        return DeltaOperation("RENAMED", contract_id, old_title, new_title=new_title)

    def _parse_removal(
        self, contract_id: str, title: str, body: str, path: str | None
    ) -> DeltaOperation:
        """删除操作必须同时提供原因和迁移方案。"""

        reason = self._field(body, "Reason")
        migration = self._field(body, "Migration")
        if not reason or not migration:
            raise SpecifyError("REMOVED 必须提供非空 Reason 和 Migration", path=path)
        return DeltaOperation(
            "REMOVED", contract_id, title, body, reason=reason, migration=migration
        )

    def _ensure_no_duplicate_operations(
        self, operations: list[DeltaOperation], path: str | None
    ) -> None:
        """同一 ID 只允许单独操作或先重命名再修改。"""

        by_id: dict[str, list[str]] = {}
        for operation in operations:
            by_id.setdefault(operation.contract_id, []).append(operation.operation)
        for contract_id, kinds in by_id.items():
            if kinds == ["RENAMED", "MODIFIED"]:
                continue
            if len(kinds) > 1:
                raise SpecifyError(
                    f"conflicting delta operations for Contract [{contract_id}]",
                    path=path,
                )

    @staticmethod
    def _field(body: str, name: str) -> str | None:
        """从独立源码行读取删除操作要求的加粗字段。"""

        match = re.search(
            rf"^\*\*{re.escape(name)}\*\*:\s*(.+?)\s*$", body, re.MULTILINE
        )
        return match.group(1).strip() if match else None

    def parse_file(self, path: Path) -> DeltaDocument:
        """读取 UTF-8 delta，并在解析错误中保留文件路径。"""

        return self.parse(path.read_text(encoding="utf-8"), path.as_posix())


_PARSER = DeltaParser()


def parse_delta(source: str, path: str | None = None) -> DeltaDocument:
    """通过统一操作语法解析 delta。"""

    return _PARSER.parse(source, path)


def parse_delta_file(path: Path) -> DeltaDocument:
    """读取并解析一份 delta 文件。"""

    return _PARSER.parse_file(path)
