"""formal Contract Markdown 解析器与稳定序列化器。"""

from __future__ import annotations

import re
from pathlib import Path

from ..contract import ContractIdentity
from ..errors import SpecifyError
from ..models import Contract, SpecDocument
from .document import MarkdownDocument, MarkdownHeading

CONTRACT_HEADING = re.compile(r"^\[([a-z0-9]+(?:-[a-z0-9]+)*)\]\s+(.+?)$")


class SpecParser:
    """使用显式 Contract ID 读写一份 formal spec。"""

    def parse(self, source: str, path: str | None = None) -> SpecDocument:
        """校验 formal spec 结构并返回完整 Contract 集合。"""

        document = MarkdownDocument(source, path)
        top_level = [item for item in document.headings if item.level == 1]
        if len(top_level) != 1 or top_level[0].title.lower() != "contract":
            raise SpecifyError(
                "spec must contain only one # contract heading", path=path
            )

        contract_section = top_level[0]
        contract_index = document.headings.index(contract_section)
        section_end = document.next_heading(contract_index, 1)
        section_limit = len(document.lines) if section_end is None else section_end

        # 只有协议级 ## 标题分隔 Contract；### 标题属于正文。
        headings = [
            item
            for item in document.headings
            if item.level == 2 and contract_section.start < item.start < section_limit
        ]
        if not headings:
            raise SpecifyError(
                "# contract must contain at least one ## [id] Contract", path=path
            )
        if document.visible_text(
            document.body_after(contract_section, headings[0].start)
        ):
            raise SpecifyError(
                "content before the first Contract is not allowed", path=path
            )
        if document.visible_text("\n".join(document.lines[: contract_section.start])):
            raise SpecifyError("content before # contract is not allowed", path=path)

        contracts = [
            self._parse_contract(document, headings, index, section_end, path)
            for index in range(len(headings))
        ]
        self._ensure_unique_identity(contracts, path)
        return SpecDocument(contracts)

    def _parse_contract(
        self,
        document: MarkdownDocument,
        headings: list[MarkdownHeading],
        index: int,
        section_end: int | None,
        path: str | None,
    ) -> Contract:
        """解析一个 ID/标题，以及其后的完整 Markdown 正文。"""

        heading = headings[index]
        match = CONTRACT_HEADING.fullmatch(heading.title)
        if not match:
            raise SpecifyError(
                f"Contract 标题格式必须为 '## [id] 标题'：{heading.title}", path=path
            )
        contract_id, title = match.groups()
        if not ContractIdentity.normalize_title(title):
            raise SpecifyError(f"Contract 标题不能为空：[{contract_id}]", path=path)
        if "->" in title:
            raise SpecifyError("Contract 标题不能包含 ->", path=path)

        next_contract = (
            headings[index + 1].start if index + 1 < len(headings) else section_end
        )
        body = document.body_after(heading, next_contract)
        if not document.visible_text(body):
            raise SpecifyError(
                f"Contract body must not be empty: [{contract_id}] {title}", path=path
            )
        return Contract(contract_id, title, body)

    def _ensure_unique_identity(
        self, contracts: list[Contract], path: str | None
    ) -> None:
        """拒绝重复的稳定 ID 和规范化展示标题。"""

        seen_ids: set[str] = set()
        seen_titles: set[str] = set()
        for contract in contracts:
            title_key = ContractIdentity.normalize_title(contract.title)
            if contract.id in seen_ids:
                raise SpecifyError(f"Contract ID 重复：{contract.id}", path=path)
            if title_key in seen_titles:
                raise SpecifyError(f"Contract 标题重复：{contract.title}", path=path)
            seen_ids.add(contract.id)
            seen_titles.add(title_key)

    def render(self, document: SpecDocument) -> str:
        """按固定空行格式序列化带显式 ID 的 formal spec。"""

        chunks = ["# contract", ""]
        for contract in document.contracts:
            chunks.extend(
                [f"## [{contract.id}] {contract.title.strip()}", "", contract.body, ""]
            )
        # 不对最终正文调用 rstrip，避免误删 Markdown 行尾空格。
        return "\n".join(chunks)

    def parse_file(self, path: Path) -> SpecDocument:
        """读取 UTF-8 formal spec，并在错误中保留文件路径。"""

        return self.parse(path.read_text(encoding="utf-8"), path.as_posix())


_PARSER = SpecParser()


def parse_spec(source: str, path: str | None = None) -> SpecDocument:
    """通过统一协议解析器解析 formal spec。"""

    return _PARSER.parse(source, path)


def parse_spec_file(path: Path) -> SpecDocument:
    """读取并解析一份 formal spec 文件。"""

    return _PARSER.parse_file(path)


def render_spec(document: SpecDocument) -> str:
    """使用规范协议标题序列化一份 formal spec。"""

    return _PARSER.render(document)
