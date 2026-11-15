"""解析器、校验器和生命周期服务共用的数据对象。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Contract:
    """Contract 使用稳定 ID 定位，标题和正文允许编辑。"""

    id: str
    title: str
    body: str


@dataclass
class SpecDocument:
    """一份 formal spec.md 中的 Contract 集合。"""

    contracts: list[Contract] = field(default_factory=list)


@dataclass(frozen=True)
class DeltaOperation:
    """针对 formal spec 中一个 Contract ID 的操作。"""

    operation: str
    contract_id: str
    title: str
    body: str = ""
    new_title: str | None = None
    reason: str | None = None
    migration: str | None = None


@dataclass
class DeltaDocument:
    """从一份 change delta 文件解析出的有序操作。"""

    operations: list[DeltaOperation] = field(default_factory=list)


@dataclass(frozen=True)
class Task:
    """带编号和完成状态的任务。"""

    number: str
    text: str
    done: bool


@dataclass
class Change:
    """从目录路径推导生命周期状态的 change。"""

    id: str
    kind: str
    status: str
    path: Path
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Issue:
    """一条可展示给用户的校验问题。"""

    message: str
    path: str | None = None

    def as_dict(self) -> dict[str, str]:
        """转换为 CLI JSON 报告使用的稳定字典结构。"""

        value = {"message": self.message}
        if self.path:
            value["path"] = self.path
        return value
