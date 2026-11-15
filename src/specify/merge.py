"""按显式 Contract ID 应用 delta。"""

from __future__ import annotations

from dataclasses import replace

from .contract import ContractIdentity
from .errors import SpecifyError
from .models import Contract, DeltaDocument, DeltaOperation, SpecDocument


class DeltaMerger:
    """预检并按协议顺序合并一份 spec 的变更。"""

    ORDER = ("RENAMED", "MODIFIED", "ADDED", "REMOVED")

    def apply(self, spec: SpecDocument, delta: DeltaDocument) -> SpecDocument:
        """在副本上完成全部操作后返回结果，不修改输入文档。"""

        contracts = list(spec.contracts)

        # 先在内存中完成验证和修改，调用方确认所有目标后再写磁盘。
        for kind in self.ORDER:
            for operation in delta.operations:
                if operation.operation == kind:
                    contracts = self._apply_one(contracts, operation)

        self._validate_unique_contracts(contracts)
        return SpecDocument(contracts)

    def _apply_one(
        self, contracts: list[Contract], operation: DeltaOperation
    ) -> list[Contract]:
        """根据操作类型分发到对应的 ID 定位逻辑。"""

        if operation.operation == "RENAMED":
            return self._rename(contracts, operation)
        if operation.operation == "MODIFIED":
            return self._modify(contracts, operation)
        if operation.operation == "ADDED":
            return self._add(contracts, operation)
        if operation.operation == "REMOVED":
            return self._remove(contracts, operation)
        raise SpecifyError(f"未知 delta 操作：{operation.operation}")

    def _rename(
        self, contracts: list[Contract], operation: DeltaOperation
    ) -> list[Contract]:
        """保留 ID，仅替换 Contract 标题。"""

        index = self._require_target(contracts, operation)
        destination = operation.new_title or ""
        self._require_title_available(
            contracts, destination, except_id=operation.contract_id
        )
        contracts[index] = replace(contracts[index], title=destination)
        return contracts

    def _modify(
        self, contracts: list[Contract], operation: DeltaOperation
    ) -> list[Contract]:
        """用 delta 给出的完整正文替换目标 Contract。"""

        index = self._require_target(contracts, operation)
        contracts[index] = replace(contracts[index], body=operation.body)
        return contracts

    def _add(
        self, contracts: list[Contract], operation: DeltaOperation
    ) -> list[Contract]:
        """新增 ID 和标题都未被占用的 Contract。"""

        if any(item.id == operation.contract_id for item in contracts):
            raise SpecifyError(f"ADDED Contract ID 已存在：{operation.contract_id}")
        self._require_title_available(contracts, operation.title)
        contracts.append(
            Contract(operation.contract_id, operation.title, operation.body)
        )
        return contracts

    def _remove(
        self, contracts: list[Contract], operation: DeltaOperation
    ) -> list[Contract]:
        """按 ID 删除 Contract，并检查 delta 标题仍指向当前版本。"""

        index = self._require_target(contracts, operation)
        return contracts[:index] + contracts[index + 1 :]

    def _require_target(
        self, contracts: list[Contract], operation: DeltaOperation
    ) -> int:
        """确认 ID 存在，且 delta 标题与当前标题一致。"""

        for index, contract in enumerate(contracts):
            if contract.id == operation.contract_id:
                if ContractIdentity.normalize_title(
                    contract.title
                ) != ContractIdentity.normalize_title(operation.title):
                    raise SpecifyError(
                        f"delta 标题与当前 Contract 不符：[{contract.id}] 当前为“{contract.title}”，delta 为“{operation.title}”"
                    )
                return index
        raise SpecifyError(
            f"delta 目标不存在：[{operation.contract_id}] {operation.title}"
        )

    def _require_title_available(
        self, contracts: list[Contract], title: str, except_id: str | None = None
    ) -> None:
        """确保规范化后的标题没有被其他 Contract 占用。"""

        wanted = ContractIdentity.normalize_title(title)
        for contract in contracts:
            if (
                contract.id != except_id
                and ContractIdentity.normalize_title(contract.title) == wanted
            ):
                raise SpecifyError(f"Contract 标题重复：{title}")

    def _validate_unique_contracts(self, contracts: list[Contract]) -> None:
        """序列化前统一检查 ID 和规范化标题唯一性。"""

        ids: set[str] = set()
        titles: set[str] = set()
        for contract in contracts:
            title = ContractIdentity.normalize_title(contract.title)
            if contract.id in ids:
                raise SpecifyError(f"Contract ID 重复：{contract.id}")
            if title in titles:
                raise SpecifyError(f"Contract 标题重复：{contract.title}")
            ids.add(contract.id)
            titles.add(title)


_MERGER = DeltaMerger()


def apply(spec: SpecDocument, delta: DeltaDocument) -> SpecDocument:
    """提供简洁调用入口，实际合并由 DeltaMerger 负责。"""

    return _MERGER.apply(spec, delta)
