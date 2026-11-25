"""识别 Markdown 中的 Contract 引用，并从正式 Spec 建立关系图。"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

from markdown_it import MarkdownIt
from markdown_it.rules_inline import StateInline

from .models import Contract, Issue, SpecDocument

_ID = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_REFERENCE = re.compile(rf"@\[({_ID}:{_ID}:{_ID})\]")


def contract_reference(state: StateInline, silent: bool) -> bool:
    """在普通 Markdown 内联内容中识别引用，保留代码和转义字符。"""

    if state.linkLevel or state.src[state.pos] != "@":
        return False
    match = _REFERENCE.match(state.src, state.pos, state.posMax)
    if match is None:
        return False
    if not silent:
        state.push("contract_reference", "", 0).content = match[1]
    state.pos = match.end()
    return True


def reference_markdown() -> MarkdownIt:
    """为校验和 Web 提供一致的 Markdown 规则；Web 另行安全渲染原始 HTML。"""

    markdown = MarkdownIt("commonmark").disable("image")
    markdown.inline.add_terminator_char("@")
    markdown.inline.ruler.before("link", "contract_reference", contract_reference)
    return markdown


class ContractLinks:
    """用稳定的完整引用维护 Contract 节点及跨文件连线。"""

    def __init__(self, documents: Mapping[Path, SpecDocument]):
        """从同一批正式文档建立索引，空文档代表已移除的 Spec。"""

        markdown = reference_markdown()
        self.contracts: dict[str, Contract] = {}
        self.edges: dict[str, tuple[str, ...]] = {}
        self.paths: dict[str, Path] = {}
        for path, document in documents.items():
            spec = f"{path.parent.parent.name}:{path.parent.name}"
            for contract in document.contracts:
                source = f"{spec}:{contract.id}"
                self.contracts[source] = contract
                self.paths[source] = path
                if "@[" not in contract.body:
                    continue
                self.edges[source] = tuple(
                    dict.fromkeys(
                        child.content
                        for block in markdown.parse(contract.body)
                        for child in block.children or []
                        if child.type == "contract_reference"
                    )
                )

    def validate(self) -> list[Issue]:
        """定位所有悬挂引用，报告来源 Contract、文件和缺失目标。"""

        return [
            Issue(
                f"Contract 引用不存在：{source} → {target}",
                str(self.paths[source]),
                "dangling-contract-reference",
                (source, target),
            )
            for source, targets in self.edges.items()
            for target in targets
            if target not in self.contracts
        ]

    def spec_edges(self) -> list[tuple[str, str]]:
        """汇总不同 Spec 之间的实际引用，保留来源和目标。"""

        edges: set[tuple[str, str]] = set()
        for source, targets in self.edges.items():
            source_spec = source.rsplit(":", 1)[0]
            for target in targets:
                target_spec = target.rsplit(":", 1)[0]
                if source_spec == target_spec or target not in self.contracts:
                    continue
                edges.add((source_spec, target_spec))
        return sorted(edges)
