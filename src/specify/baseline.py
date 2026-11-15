"""显式捕获 change delta 所依赖的 Contract 正文版本。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .config import dump_yaml, load_config
from .contract import ContractIdentity
from .errors import SpecifyError
from .merge import DeltaMerger
from .models import Change, SpecDocument
from .parse.delta import parse_delta_file
from .parse.spec import parse_spec_file
from .paths import RepoPaths, validate_id
from .validate.changes import read_metadata


class BaselineCapture:
    """从作者已完成的 delta 明确生成 baseVersions。"""

    def __init__(self, paths: RepoPaths):
        """绑定仓库路径和 delta 语义校验器。"""

        self.paths = paths
        self.merger = DeltaMerger()

    def capture(self, change: Change) -> dict[str, str]:
        """校验 delta 目标后写入当前正文 hash，并返回生成的映射。"""

        if change.status not in {"proposed", "implemented"}:
            raise SpecifyError("只能为 proposed 或 implemented change 捕获基线")
        metadata = read_metadata(change)
        if "sync" in metadata:
            raise SpecifyError("change 已成功 sync；后续语义调整必须另建 change")
        if "affects" not in metadata:
            raise SpecifyError("无 spec 影响的 change 不需要 Contract 基线")
        if not (change.path / "change.md").is_file():
            raise SpecifyError("缺少 change.md", path=str(change.path))

        config = load_config(self.paths)
        targets = metadata["affects"]
        if not isinstance(targets, list) or not targets:
            raise SpecifyError("affects 必须是非空列表")
        expected_paths: set[str] = set()
        for target in targets:
            if not isinstance(target, dict):
                raise SpecifyError("affects 中的每一项必须是映射")
            expected_paths.add(f"{target.get('type')}/{target.get('id')}.md")
        actual_paths = {
            path.relative_to(change.path / "deltas").as_posix()
            for path in (change.path / "deltas").glob("*/*.md")
        }
        if actual_paths != expected_paths:
            raise SpecifyError(
                f"delta 文件与 affects 不匹配：应为 {sorted(expected_paths)}，实际为 {sorted(actual_paths)}"
            )

        baselines: dict[str, str] = {}
        for target in targets:
            self._capture_target(change, target, config, baselines)

        # YAML 基线只在显式命令调用时更新，verify/sync 都保持只读。
        if baselines:
            metadata["baseVersions"] = dict(sorted(baselines.items()))
        else:
            metadata.pop("baseVersions", None)
        metadata["updatedAt"] = (
            datetime.now().astimezone().isoformat(timespec="seconds")
        )
        dump_yaml(change.path / "meta-data.yaml", metadata)
        return baselines

    def _capture_target(
        self,
        change: Change,
        target: dict[str, Any],
        config: dict[str, Any],
        baselines: dict[str, str],
    ) -> None:
        """校验一个 spec 的 delta，并为需要旧正文的 ID 记录 hash。"""

        spec_type, spec_id, operation = (
            target.get("type"),
            target.get("id"),
            target.get("change"),
        )
        if (
            spec_type not in config["specTypes"]
            or not isinstance(spec_id, str)
            or not validate_id(spec_id)
            or operation not in {"create", "modify", "remove"}
        ):
            raise SpecifyError("affects target 使用了无效的 spec type 或操作")
        spec_path = self.paths.specs / spec_type / spec_id / "spec.md"
        delta_path = change.path / "deltas" / spec_type / f"{spec_id}.md"
        delta = parse_delta_file(delta_path)
        current = parse_spec_file(spec_path) if spec_path.is_file() else SpecDocument()

        if operation == "create" and spec_path.exists():
            raise SpecifyError(f"create 目标 spec 已存在：{spec_type}:{spec_id}")
        if operation != "create" and not spec_path.is_file():
            raise SpecifyError(f"目标 spec 不存在：{spec_type}:{spec_id}")

        # 使用合并器验证 ID、标题和新增冲突，但不写入任何正式 spec。
        updated = self.merger.apply(current, delta)
        if operation == "create" and any(
            item.operation != "ADDED" for item in delta.operations
        ):
            raise SpecifyError("create 目标只能包含 ADDED 操作")
        if operation == "remove" and (
            any(item.operation != "REMOVED" for item in delta.operations)
            or updated.contracts
        ):
            raise SpecifyError("remove 目标必须移除 spec 内的全部 Contracts")
        if operation == "modify" and not updated.contracts:
            raise SpecifyError("modify 操作不能删除整个 spec")

        current_by_id = {contract.id: contract for contract in current.contracts}
        for item in delta.operations:
            if item.operation not in {"MODIFIED", "REMOVED", "RENAMED"}:
                continue
            contract = current_by_id[item.contract_id]
            reference = f"{spec_type}:{spec_id}:{contract.id}"
            baselines[reference] = ContractIdentity.body_hash(contract.body)


def capture_baselines(paths: RepoPaths, change: Change) -> dict[str, str]:
    """提供给 CLI 的基线捕获入口。"""

    return BaselineCapture(paths).capture(change)
