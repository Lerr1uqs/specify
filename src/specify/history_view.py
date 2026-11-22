"""为历史查询提供结构化导出与 Rich 终端视图。"""

from __future__ import annotations

import csv
from io import StringIO
from typing import ClassVar

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .history import HistoryRecord


class HistoryView:
    """用同一组可见记录生成公开字段和人类视图。"""

    fields = ("idx", "action", "date", "changeId", "source", "title", "content")

    @classmethod
    def entry(cls, record: HistoryRecord) -> dict[str, object]:
        """公开历史字段，保留回执关联值在项目内部。"""

        return {key: value for key, value in record.items() if key in cls.fields}

    @classmethod
    def csv(cls, reference: str, records: list[HistoryRecord]) -> str:
        """导出带完整引用的 CSV，按标准规则引用多行 Markdown。"""

        buffer = StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=("ref", *cls.fields))
        writer.writeheader()
        for record in records:
            writer.writerow({"ref": reference, **cls.entry(record)})
        return buffer.getvalue()


class HumanHistory:
    """按最近版本、变更表格、diff 组织 Rich 终端输出。"""

    action_styles: ClassVar[dict[str, str]] = {
        "add": "green",
        "modify": "yellow",
        "remove": "red",
    }

    def __init__(self, console: Console):
        """保存命令的 stdout 控制台，沿用终端颜色和宽度检测。"""

        self.console = console

    def latest(self, reference: str, record: HistoryRecord | None) -> None:
        """展示最新正文，或显示尚无历史和已删除状态。"""

        subtitle: Text | None = None
        body: Text | Markdown
        if record is None:
            body = Text("暂无历史")
        else:
            action = record["action"]
            subtitle = Text(f"#{record['idx']} · {action} · {record['date']}")
            if action == "remove":
                body = Text("已删除", style=self.action_styles[action])
            else:
                body = Markdown(f"## {record['title']}\n\n{record['content']}")
        self.console.print(Panel(body, title=Text(reference), subtitle=subtitle))

    def timeline(self, reference: str, records: list[HistoryRecord]) -> None:
        """按版本从新到旧展示操作、时间和正文。"""

        title = Text(f"{reference} · 历史")
        if not records:
            self.console.print(Panel(Text("没有可展示的记录"), title=title))
            return
        table = Table(title=title, expand=True, show_lines=True)
        table.add_column("版本", justify="right", no_wrap=True)
        table.add_column("操作", no_wrap=True)
        table.add_column("时间", overflow="fold")
        table.add_column("Change", overflow="fold")
        table.add_column("标题 / 正文", overflow="fold", ratio=1)
        # 查询结果按写入顺序传入，终端表格先展示最新版本。
        for record in reversed(records):
            action = record["action"]
            origin = record["changeId"] or "—"
            if record["source"] == "backfill":
                origin = f"{origin}（回填）" if record["changeId"] else "回填"
            snapshot = "\n".join(filter(None, (record["title"], record["content"])))
            table.add_row(
                f"#{record['idx']}",
                Text(action, style=self.action_styles[action]),
                record["date"],
                Text(origin),
                Text(snapshot) if snapshot else Text("已删除", style="dim"),
            )
        self.console.print(table)

    def diff(self, reference: str, start: int, end: int, change: str) -> None:
        """使用统一 diff 标出新增和删除的标题或正文行。"""

        body = Syntax(change, "diff", word_wrap=True) if change else Text("内容相同")
        self.console.print(Panel(body, title=Text(f"{reference} · #{start} → #{end}")))
