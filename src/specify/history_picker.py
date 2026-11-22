"""发现、匹配并在终端中选择 Contract 历史引用。"""

from __future__ import annotations

import os
import select
import sys

from rich.console import Console, Group
from rich.live import Live
from rich.text import Text

from .errors import UsageError
from .history import ContractRef
from .index import list_specs
from .parse.spec import parse_spec_file
from .paths import RepoPaths


class HistoryReferenceCatalog:
    """从正式 spec 与历史快照建立稳定的引用候选集合。"""

    def __init__(self, paths: RepoPaths, config: dict[str, object]):
        """绑定项目路径和已经校验的配置。"""

        self.paths = paths
        self.config = config

    def references(self) -> list[str]:
        """合并当前 Contract 和历史目录引用，并排序去重。"""

        references: set[ContractRef] = set()
        # 正式 spec 提供当前 Contract，即使它尚无历史文件也可供选择。
        for spec_type, spec_id in list_specs(self.paths, self.config):
            path = self.paths.specs / spec_type / spec_id / "spec.md"
            for contract in parse_spec_file(path).contracts:
                references.add((spec_type, spec_id, contract.id))

        # 历史路径保留已删除 Contract 的引用，后续展示仍遵循 include-removed。
        for path in self.paths.contract_history.glob("*/*/*.jsonl"):
            if path.is_file():
                references.add((path.parent.parent.name, path.parent.name, path.stem))
        return sorted(":".join(reference) for reference in references)

    @staticmethod
    def search(references: list[str], query: str) -> list[tuple[str, tuple[int, ...]]]:
        """返回整条引用的模糊匹配结果和命中位置，较紧凑的结果优先。"""

        query = query.strip().lower()
        if not query:
            return [(reference, ()) for reference in references]

        matches: list[tuple[str, tuple[int, ...]]] = []
        for reference in references:
            text = reference.lower()
            start = text.find(query)
            if start >= 0:
                matches.append((reference, tuple(range(start, start + len(query)))))
                continue

            # 字符可以在同一段内命中，也可以跳过连字符和冒号跨段命中。
            positions: list[int] = []
            position = -1
            for character in query:
                position = text.find(character, position + 1)
                if position < 0:
                    break
                positions.append(position)
            else:
                matches.append((reference, tuple(positions)))

        # 优先显示连续匹配，同等跨度下优先显示命中位置靠前的引用。
        matches.sort(key=lambda match: (match[1][-1] - match[1][0], match[1][0]))
        return matches


def _render_picker(
    query: str,
    matches: list[tuple[str, tuple[int, ...]]],
    selected: int,
    offset: int,
    height: int,
) -> Group:
    """生成搜索栏、带三段配色的候选列表与键盘提示。"""

    search = Text("❯ ", style="bold bright_cyan", no_wrap=True, overflow="ellipsis")
    search.append(query or "输入字符筛选", style="bold" if query else "dim")
    lines = [Text("查询 Contract 历史", style="bold"), search, Text()]

    visible = matches[offset : offset + height]
    for index, (reference, positions) in enumerate(visible, offset):
        active = index == selected
        row = Text("▸ " if active else "  ", no_wrap=True, overflow="ellipsis")
        row.stylize("bold bright_cyan", 0, 2)
        for part_index, (part, color) in enumerate(
            zip(reference.split(":"), ("cyan", "magenta", "green"))
        ):
            if part_index:
                row.append(":", style="dim")
            row.append(part, style=f"bold {color}" if active else color)

        # 在分段配色上标出实际命中的字符，前两个字符是选择标记。
        for position in positions:
            row.stylize("bold underline bright_yellow", position + 2, position + 3)
        lines.append(row)

    if not matches:
        lines.append(Text("没有匹配的引用", style="dim"))
    count = Text(f"{len(matches)} 项匹配", style="bold")
    remaining = len(matches) - offset - len(visible)
    if offset:
        count.append(f"  ↑ 上方 {offset} 项", style="dim")
    if remaining:
        count.append(f"  ↓ 下方 {remaining} 项", style="dim")
    count.no_wrap = True
    count.overflow = "ellipsis"
    keys = Text("↑↓ 移动   Enter 查询   Esc 取消", style="dim", no_wrap=True)
    return Group(*lines, Text(), count, keys)


def choose_history_reference(references: list[str], console: Console) -> str | None:
    """读取终端按键完成实时筛选，取消时返回 None。"""

    if not references:
        raise UsageError("当前项目没有可查询的 Contract 引用")
    if sys.platform == "win32":
        raise UsageError("当前终端不支持历史选择，请传入完整 Contract 引用")

    import termios
    import tty

    descriptor = sys.stdin.fileno()
    original = termios.tcgetattr(descriptor)
    query = ""
    selected = 0
    offset = 0
    try:
        # 逐键读取，同时保留终端的换行处理和 Ctrl+C 行为。
        tty.setcbreak(descriptor)
        with Live(console=console, screen=True, auto_refresh=False) as live:
            while True:
                matches = HistoryReferenceCatalog.search(references, query)
                height = max(1, console.size.height - 6)
                selected = min(selected, max(0, len(matches) - 1))
                offset = min(offset, selected)
                if selected >= offset + height:
                    offset = selected - height + 1

                # 整屏一次刷新，显示窗口外的候选仍参与匹配。
                live.update(
                    _render_picker(query, matches, selected, offset, height),
                    refresh=True,
                )

                key = os.read(descriptor, 1)
                if key in (b"\r", b"\n"):
                    if matches:
                        return matches[selected][0]
                elif key == b"\x1b":
                    # 方向键由 Esc 和后续字节组成，短暂等待以区分单独的 Esc。
                    if not select.select([descriptor], [], [], 0.05)[0]:
                        return None
                    prefix = os.read(descriptor, 1)
                    if (
                        prefix in (b"[", b"O")
                        and select.select([descriptor], [], [], 0.05)[0]
                    ):
                        direction = os.read(descriptor, 1)
                        if direction == b"A":
                            selected = max(0, selected - 1)
                        elif direction == b"B":
                            selected = min(max(0, len(matches) - 1), selected + 1)
                elif key in (b"\x7f", b"\b"):
                    query = query[:-1]
                    selected = offset = 0
                elif not key:
                    return None
                elif b" " <= key <= b"~":
                    query += key.decode("ascii")
                    selected = offset = 0
    finally:
        # 不论确认、取消还是异常，都恢复用户原有的终端模式。
        termios.tcsetattr(descriptor, termios.TCSADRAIN, original)
