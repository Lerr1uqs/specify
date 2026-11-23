"""按完整 Contract 引用保存与查询已生效的版本。"""

from __future__ import annotations

import json
from datetime import datetime
from difflib import unified_diff
from pathlib import Path
from typing import Any, Literal, TypedDict

from .errors import SpecifyError, UsageError
from .index import list_specs
from .io import atomic_write
from .models import Change, Contract, SpecDocument
from .parse.spec import parse_spec_file
from .paths import RepoPaths, scan_changes, validate_id
from .validate.changes import read_metadata

Action = Literal["add", "modify", "remove"]
ContractRef = tuple[str, str, str]


class HistoryRecord(TypedDict):
    """JSONL 中的一条变迁；historyId 关联本次同步的成功回执。"""

    idx: int
    action: Action
    date: str
    changeId: str | None
    source: Literal["backfill", "sync"]
    title: str
    content: str
    historyId: str | None


class ContractHistory:
    """管理各条 Contract 独立的 JSONL，沿用 change 回执发布本次记录。"""

    def __init__(self, paths: RepoPaths):
        """绑定项目路径，并在单次操作内复用已读取的回执。"""

        self.paths = paths
        self._changes: dict[str, Change] | None = None
        self._receipts: dict[str, str | None] = {}

    @staticmethod
    def parse_ref(reference: str) -> ContractRef:
        """在 CLI 边界校验三段引用，方便查询已经删除的 spec。"""

        parts = reference.split(":")
        if len(parts) != 3 or not all(validate_id(part) for part in parts):
            raise UsageError("history 参数必须是 <type>:<spec-id>:<contract-id>")
        spec_type, spec_id, contract_id = parts
        return spec_type, spec_id, contract_id

    def read(self, reference: ContractRef) -> list[HistoryRecord]:
        """只读取已有快照，跳过尚无成功回执的同步记录。"""

        path = self._path(reference)
        if not path.is_file():
            return []

        rows: list[HistoryRecord] = []
        with path.open(encoding="utf-8", newline="\n") as stream:
            for number, line in enumerate(stream, 1):
                try:
                    record: HistoryRecord = json.loads(line)
                except json.JSONDecodeError as error:
                    raise SpecifyError(
                        f"第 {number} 行历史记录不是有效 JSON", path=str(path)
                    ) from error

                token = record["historyId"]
                if (
                    token is None
                    or self._published_token(record["changeId"] or "") == token
                ):
                    rows.append(record)
        return rows

    def stage_sync(
        self,
        change_id: str,
        history_id: str,
        at: datetime,
        updates: dict[Path, tuple[SpecDocument, SpecDocument]],
    ) -> None:
        """同步正式文件前保存有变化的 Contract，等待回执生效。"""

        for path, (before, after) in updates.items():
            old = {contract.id: contract for contract in before.contracts}
            new = {contract.id: contract for contract in after.contracts}
            spec_type, spec_id = path.parent.parent.name, path.parent.name
            for contract_id in sorted(old.keys() | new.keys()):
                previous, current = old.get(contract_id), new.get(contract_id)
                if previous == current:
                    continue
                reference = spec_type, spec_id, contract_id
                rows = self.read(reference)

                # 直接编辑过的正式正文也要保留，才能还原本次同步前的实际内容。
                if previous is not None:
                    self._append_snapshot(rows, previous, at, change_id, history_id)
                action: Action = (
                    "add"
                    if previous is None
                    else "remove"
                    if current is None
                    else "modify"
                )
                rows.append(
                    HistoryRecord(
                        idx=rows[-1]["idx"] + 1 if rows else 1,
                        action=action,
                        date=at.isoformat(timespec="seconds", sep=" "),
                        changeId=change_id,
                        source="sync",
                        title=current.title if current else "",
                        content=current.body if current else "",
                        historyId=history_id,
                    )
                )
                self._write(reference, rows)

    def capture_baseline(
        self, reference: ContractRef, contract: Contract, at: datetime
    ) -> None:
        """保存已捕获基线的正式正文，供草稿按 hash 查回。"""

        rows = self.read(reference)
        if self._append_snapshot(rows, contract, at):
            self._write(reference, rows)

    def backfill(self, config: dict[str, Any], at: datetime) -> int:
        """为还没有历史的现存 Contract 补写一条 add 快照。"""

        count = 0
        for spec_type, spec_id in list_specs(self.paths, config):
            path = self.paths.specs / spec_type / spec_id / "spec.md"
            for contract in parse_spec_file(path).contracts:
                reference = spec_type, spec_id, contract.id
                # 回填仅补缺失文件，保留已有记录与等待回执的同步快照。
                if not self._path(reference).is_file():
                    rows: list[HistoryRecord] = []
                    self._append_snapshot(rows, contract, at)
                    self._write(reference, rows)
                    count += 1
        return count

    def _published_token(self, change_id: str) -> str | None:
        """仅为历史引用到的 implemented 或 archived change 读取回执。"""

        if self._changes is None:
            self._changes = {
                change.id: change
                for change in scan_changes(self.paths)
                if change.status in {"implemented", "archived"}
            }
        if change_id not in self._receipts:
            change = self._changes.get(change_id)
            receipt = read_metadata(change).get("sync") if change else None
            self._receipts[change_id] = (
                receipt.get("historyId")
                if isinstance(receipt, dict) and receipt.get("appliedAt")
                else None
            )
        return self._receipts[change_id]

    def _path(self, reference: ContractRef) -> Path:
        """以 spec type、spec ID、Contract ID 将同名 Contract 分开。"""

        spec_type, spec_id, contract_id = reference
        return (
            self.paths.contract_history / spec_type / spec_id / f"{contract_id}.jsonl"
        )

    @staticmethod
    def _append_snapshot(
        rows: list[HistoryRecord],
        contract: Contract,
        at: datetime,
        change_id: str | None = None,
        history_id: str | None = None,
    ) -> bool:
        """记录观察到的正式版本，连续相同的标题和正文共用一条快照。"""

        latest = rows[-1] if rows else None
        active = latest is not None and latest["action"] != "remove"
        if (
            active
            and latest["title"] == contract.title
            and latest["content"] == contract.body
        ):
            return False
        rows.append(
            HistoryRecord(
                idx=latest["idx"] + 1 if latest else 1,
                action="modify" if active else "add",
                date=at.isoformat(timespec="seconds", sep=" "),
                changeId=change_id,
                source="backfill",
                title=contract.title,
                content=contract.body,
                historyId=history_id,
            )
        )
        return True

    def _write(self, reference: ContractRef, rows: list[HistoryRecord]) -> None:
        """原子写入完整 JSONL，重试时自然替换同一条 Contract 的未生效记录。"""

        content = "".join(
            json.dumps(record, ensure_ascii=False) + "\n" for record in rows
        )
        atomic_write(self._path(reference), content)


def active_history(records: list[HistoryRecord]) -> list[HistoryRecord]:
    """从最新一次删除之后开始，返回当前这一轮的记录。"""

    for index in range(len(records) - 1, -1, -1):
        if records[index]["action"] == "remove":
            return records[index + 1 :]
    return records


def diff_history(
    reference: str, records: list[HistoryRecord], start: int, end: int
) -> str:
    """使用稳定 idx 比较两份快照，删除状态视为空文档。"""

    versions = {record["idx"]: record for record in records}
    for index in (start, end):
        if index not in versions:
            raise UsageError(f"不存在历史版本 #{index}")

    # 将标题与正文分别纳入 diff，重命名也有清晰的差异。
    documents = []
    for version in (versions[start], versions[end]):
        document = f"## {version['title']}\n\n{version['content']}"
        documents.append([] if version["action"] == "remove" else document.split("\n"))
    return "\n".join(
        unified_diff(
            *documents,
            fromfile=f"{reference}@{start}",
            tofile=f"{reference}@{end}",
            lineterm="",
        )
    )
