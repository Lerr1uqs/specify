"""保留源码行号的 Markdown 协议文档解析。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from markdown_it import MarkdownIt

from ..errors import SpecifyError


@dataclass(frozen=True)
class MarkdownHeading:
    """顶层 Markdown 标题及其从零开始的源码行范围。"""

    level: int
    title: str
    start: int
    end: int


class MarkdownDocument:
    """解析协议标题，同时保留原始 Markdown 源码。"""

    def __init__(self, source: str, path: str | None = None):
        """一次解析所有标题，让调用方共用同一套边界规则。"""

        self.source = source.replace("\r\n", "\n").replace("\r", "\n")
        self.lines = self.source.splitlines()
        self.path = path
        self.headings = self._read_protocol_headings()

    def _read_protocol_headings(self) -> list[MarkdownHeading]:
        """收集代码块、引用块和列表容器之外的协议标题。"""

        tokens = MarkdownIt("commonmark").parse(self.source)
        result: list[MarkdownHeading] = []
        for index, token in enumerate(tokens):
            # 引用块或列表里的标题 token level 非零，不能当作协议分隔符。
            if token.type != "heading_open" or not token.map or token.level != 0:
                continue
            if index + 1 >= len(tokens) or tokens[index + 1].type != "inline":
                raise SpecifyError("heading has no title", path=self.path)
            result.append(
                MarkdownHeading(
                    level=int(token.tag[1:]),
                    title=tokens[index + 1].content.strip(),
                    start=token.map[0],
                    end=token.map[1],
                )
            )
        return result

    def body_after(self, heading: MarkdownHeading, stop: int | None) -> str:
        """返回标题后的源码，并且只裁掉正文边缘空行。"""

        end = len(self.lines) if stop is None else stop
        body_lines = self.lines[heading.end : end]

        # 保留正文内部空白，让版本 hash 反映实际编辑。
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        while body_lines and not body_lines[-1].strip():
            body_lines.pop()
        return "\n".join(body_lines)

    def next_heading(self, index: int, max_level: int) -> int | None:
        """查找结束当前段落的下一个协议标题。"""

        for heading in self.headings[index + 1 :]:
            if heading.level <= max_level:
                return heading.start
        return None

    @staticmethod
    def visible_text(source: str) -> str:
        """判断内容是否包含有效文本时忽略 HTML 注释。"""

        return re.sub(r"<!--.*?-->", "", source, flags=re.DOTALL).strip()
