"""变更元数据、delta 语义与生命周期校验。"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ..config import load_yaml
from ..contract import ContractIdentity
from ..errors import SpecifyError
from ..merge import DeltaMerger
from ..models import CHANGE_PRIORITIES, Change, DeltaDocument, Issue, SpecDocument
from ..parse.delta import parse_delta_file
from ..parse.spec import parse_spec_file
from ..parse.tasks import parse_tasks_file
from ..paths import RepoPaths, scan_changes, validate_id

HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MERGER = DeltaMerger()


def read_metadata(change: Change) -> dict[str, Any]:
    """读取 YAML，并校验与 change 目录重复的身份字段。"""

    path = change.path / "meta-data.yaml"
    metadata = load_yaml(path)
    if metadata.get("id") != change.id:
        raise SpecifyError("metadata id 与目录名不一致", path=str(path))
    if metadata.get("kind") != change.kind:
        raise SpecifyError("metadata kind 与目录层级不一致", path=str(path))
    if not validate_id(change.id):
        raise SpecifyError("change id 必须为 kebab-case", path=str(path))
    return metadata


class ChangeValidator:
    """校验一个 change 的文件、元数据、任务和 delta。"""

    def __init__(self, paths: RepoPaths, config: dict[str, Any]):
        """保存项目路径与已校验配置，供各阶段复用。"""

        self.paths = paths
        self.config = config

    def validate(
        self, change: Change, require_complete_tasks: bool = False
    ) -> list[Issue]:
        """收集一个 change 的首个结构性错误，且不修改任何文件。"""

        try:
            metadata = self.read_metadata(change)
            change.metadata = metadata
            self._validate_context_document(change)
            self._validate_status_fields(change, metadata)
            self._validate_identity_and_times(change, metadata)

            # 需求录入阶段只校验身份和说明。拒绝的需求也可能尚未完成拆解。
            if change.status == "proposed" or (
                change.status == "rejected"
                and not {"affects", "specImpact"} & metadata.keys()
            ):
                return []
            targets = self._validate_metadata(change, metadata)

            if change.status != "rejected":
                tasks_path = change.path / "tasks.md"
                if not tasks_path.is_file():
                    raise SpecifyError("缺少 tasks.md", path=str(tasks_path))
                tasks = parse_tasks_file(tasks_path)
                if require_complete_tasks and not all(task.done for task in tasks):
                    raise SpecifyError("执行该生命周期操作前必须完成所有 tasks")
                self._validate_deltas(change, metadata, targets)
        except SpecifyError as exc:
            return [Issue(exc.message, str(exc.path or change.path))]
        return []

    def read_metadata(self, change: Change) -> dict[str, Any]:
        """读取 YAML，并校验与 change 目录重复的身份字段。"""

        return read_metadata(change)

    def _validate_context_document(self, change: Change) -> None:
        """要求每个 change 有单一、可自由组织内容的 change.md。"""

        if not (change.path / "change.md").is_file():
            raise SpecifyError("缺少 change.md", path=str(change.path))

    def _validate_status_fields(self, change: Change, metadata: dict[str, Any]) -> None:
        """限制拒绝原因只出现在 rejected 状态。"""

        if (
            change.status == "rejected"
            and not str(metadata.get("rejectedReason", "")).strip()
        ):
            raise SpecifyError("rejected change 必须填写 rejectedReason")
        if change.status != "rejected" and "rejectedReason" in metadata:
            raise SpecifyError("rejectedReason 只能用于 rejected change")
        if change.status == "rejected" and "sync" in metadata:
            raise SpecifyError("rejected change 不应带有 sync 回执")
        if "sync" in metadata and change.status != "implemented":
            raise SpecifyError("sync 回执只允许出现在 implemented change")

    def _validate_metadata(
        self, change: Change, metadata: dict[str, Any]
    ) -> dict[str, dict[str, Any]]:
        """校验 affects/specImpact 二选一，并返回按 spec 引用索引的目标。"""

        has_affects = "affects" in metadata
        has_impact = "specImpact" in metadata
        if not has_affects and not has_impact:
            raise SpecifyError(
                "尚未声明 Spec 影响，请通过 change process 指定 --affect 或 --no-spec-impact"
            )
        if has_affects and has_impact:
            raise SpecifyError(
                "meta-data.yaml 必须且只能包含 affects 或 specImpact 之一"
            )
        if has_impact:
            impact = metadata["specImpact"]
            if (
                not isinstance(impact, dict)
                or impact.get("kind") != "none"
                or not str(impact.get("reason", "")).strip()
            ):
                raise SpecifyError("specImpact.kind: none 必须提供 reason")
            if (change.path / "deltas").exists():
                raise SpecifyError("无 spec 影响的 change 不能包含 deltas/ 目录")
            if "baseVersions" in metadata or "sync" in metadata:
                raise SpecifyError(
                    "无 spec 影响的 change 不能包含 baselines 或 sync 回执"
                )
            return {}

        targets: dict[str, dict[str, Any]] = {}
        affects = metadata["affects"]
        if not isinstance(affects, list) or not affects:
            raise SpecifyError("affects 必须是非空列表")
        for target in affects:
            if not isinstance(target, dict):
                raise SpecifyError("affects 中的每一项必须是映射")
            spec_type = target.get("type")
            spec_id = target.get("id")
            if spec_type not in self.config["specTypes"] or not validate_id(
                str(spec_id or "")
            ):
                raise SpecifyError(
                    "affects target 必须使用已配置类型和 kebab-case spec id"
                )
            if target.get("change") not in {"create", "modify", "remove"}:
                raise SpecifyError(f"affects target 操作无效：{spec_type}:{spec_id}")
            reference = f"{spec_type}:{spec_id}"
            if reference in targets:
                raise SpecifyError(f"affects 中有重复目标：{reference}")
            targets[reference] = target
        return targets

    def _validate_identity_and_times(
        self, change: Change, metadata: dict[str, Any]
    ) -> None:
        """校验可读标题、配置引用和带时区的创建/更新时间。"""

        allowed = {
            "id",
            "title",
            "kind",
            "priority",
            "createdAt",
            "updatedAt",
            "affects",
            "specImpact",
            "baseVersions",
            "sync",
            "rejectedReason",
        }
        unknown = set(metadata) - allowed
        if unknown:
            raise SpecifyError(
                f"meta-data.yaml 包含未知字段：{', '.join(sorted(unknown))}"
            )
        if not isinstance(metadata.get("title"), str) or not metadata["title"].strip():
            raise SpecifyError("metadata title 必须是非空文本")
        if change.kind not in self.config["kinds"]:
            raise SpecifyError(f"change kind 未在 config.yaml 中声明：{change.kind}")
        if "priority" in metadata and metadata["priority"] not in CHANGE_PRIORITIES:
            raise SpecifyError(f"priority 必须是 {', '.join(CHANGE_PRIORITIES)} 之一")

        created = self._parse_timestamp(metadata.get("createdAt"), "createdAt")
        updated = self._parse_timestamp(metadata.get("updatedAt"), "updatedAt")
        if updated < created:
            raise SpecifyError("updatedAt 不能早于 createdAt")

    @staticmethod
    def _parse_timestamp(value: Any, field: str) -> datetime:
        """把 YAML 时间值转成带时区的 datetime。"""

        if isinstance(value, datetime):
            timestamp = value
        elif isinstance(value, str):
            try:
                timestamp = datetime.fromisoformat(value)
            except ValueError as exc:
                raise SpecifyError(f"{field} 不是有效的 RFC 3339 时间") from exc
        else:
            raise SpecifyError(f"{field} 必须是带时区的 RFC 3339 时间")
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise SpecifyError(f"{field} 必须包含时区")
        return timestamp

    def _validate_deltas(
        self,
        change: Change,
        metadata: dict[str, Any],
        targets: dict[str, dict[str, Any]],
    ) -> None:
        """校验 delta 文件集合、操作目标、基线与 sync 回执。"""

        delta_root = change.path / "deltas"
        actual = (
            {
                f"{path.parent.name}:{path.stem}": path
                for path in delta_root.glob("*/*.md")
            }
            if delta_root.is_dir()
            else {}
        )
        if set(actual) != set(targets):
            raise SpecifyError(
                f"delta 文件与 affects 不匹配：应为 {sorted(targets)}，实际为 {sorted(actual)}"
            )

        delta_hashes = self._delta_hashes(actual)
        is_synced = self._validate_sync_receipt(metadata, delta_hashes)
        if is_synced:
            return

        required_baselines: dict[str, str] = {}
        for reference, target in targets.items():
            spec_type, spec_id = reference.split(":", 1)
            delta = parse_delta_file(actual[reference])
            required_baselines.update(
                self._validate_target(spec_type, spec_id, target, delta)
            )
        self._validate_baselines(metadata.get("baseVersions"), required_baselines)

    def _validate_target(
        self,
        spec_type: str,
        spec_id: str,
        target: dict[str, Any],
        delta: DeltaDocument,
    ) -> dict[str, str]:
        """校验单个 delta 与其 formal spec 的当前版本一致。"""

        reference = f"{spec_type}:{spec_id}"
        spec_path = self.paths.specs / spec_type / spec_id / "spec.md"
        exists = spec_path.is_file()
        operation_kinds = {operation.operation for operation in delta.operations}
        if target["change"] == "create":
            if exists:
                raise SpecifyError(f"create 目标 spec 已存在：{reference}")
            if operation_kinds != {"ADDED"}:
                raise SpecifyError(f"create 目标只能包含 ADDED 操作：{reference}")
            MERGER.apply(SpecDocument(), delta)
            return {}

        if not exists:
            raise SpecifyError(f"目标 spec 不存在：{reference}")
        current = parse_spec_file(spec_path)
        updated = MERGER.apply(current, delta)
        if target["change"] == "remove":
            if operation_kinds != {"REMOVED"} or updated.contracts:
                raise SpecifyError(
                    f"remove 目标必须移除 spec 内的全部 Contracts：{reference}"
                )
        elif target["change"] == "modify" and not updated.contracts:
            raise SpecifyError(f"modify 操作不能删除整个 spec：{reference}")

        current_by_id = {contract.id: contract for contract in current.contracts}
        return {
            f"{spec_type}:{spec_id}:{operation.contract_id}": ContractIdentity.body_hash(
                current_by_id[operation.contract_id].body
            )
            for operation in delta.operations
            if operation.operation in {"MODIFIED", "REMOVED", "RENAMED"}
        }

    def _validate_baselines(self, value: Any, expected: dict[str, str]) -> None:
        """要求 YAML 精确记录所有正文变更操作的 64 位 hash。"""

        if not expected:
            if value not in (None, {}):
                raise SpecifyError(
                    "没有 MODIFIED/REMOVED/RENAMED 操作时不能有 baseVersions"
                )
            return
        expected_keys = set(expected)
        if not isinstance(value, dict) or set(value) != expected_keys:
            missing = (
                sorted(expected_keys - set(value or {}))
                if isinstance(value, dict)
                else sorted(expected_keys)
            )
            extra = (
                sorted(set(value) - expected_keys) if isinstance(value, dict) else []
            )
            raise SpecifyError(
                f"baseVersions 键必须与 delta 目标一致；缺少 {missing}，多余 {extra}"
            )
        for reference, digest in value.items():
            if not isinstance(digest, str) or not HASH_PATTERN.fullmatch(digest):
                raise SpecifyError(
                    f"baseVersions 中的 hash 必须是 64 位小写 SHA-256：{reference}"
                )
            if digest != expected[reference]:
                raise SpecifyError(
                    f"Contract 正文基线已变化：{reference}，请按当前正文调整 delta 和 hash"
                )

    @staticmethod
    def _delta_hashes(files: dict[str, Path]) -> dict[str, str]:
        """对 delta 原始字节计算回执 hash，避免换行转换影响归档审计。"""

        return {
            path.relative_to(path.parents[1]).as_posix(): ContractIdentity.file_hash(
                path.read_bytes()
            )
            for path in files.values()
        }

    @staticmethod
    def _validate_sync_receipt(
        metadata: dict[str, Any], current_hashes: dict[str, str]
    ) -> bool:
        """验证已有回执；内容变化后拒绝重复应用而不是重放 delta。"""

        receipt = metadata.get("sync")
        if receipt is None:
            return False
        if not isinstance(receipt, dict) or not isinstance(
            receipt.get("deltaHashes"), dict
        ):
            raise SpecifyError("sync 回执格式无效")
        if receipt["deltaHashes"] != current_hashes:
            raise SpecifyError(
                "sync 回执已过期；成功 sync 后不能修改 delta，请另建 follow-up change"
            )
        if not receipt.get("appliedAt"):
            raise SpecifyError("sync 回执缺少 appliedAt")
        return True


def validate_change(
    paths: RepoPaths,
    config: dict[str, Any],
    change: Change,
    require_complete_tasks: bool = False,
) -> list[Issue]:
    """校验单个 change，供 CLI 和生命周期服务调用。"""

    return ChangeValidator(paths, config).validate(change, require_complete_tasks)


def validate_changes(
    paths: RepoPaths,
    config: dict[str, Any],
    require_complete_tasks: bool = False,
) -> list[Issue]:
    """按目录状态遍历并校验所有非 archived change。"""

    validator = ChangeValidator(paths, config)
    issues: list[Issue] = []
    for change in scan_changes(paths):
        if change.status != "archived":
            issues.extend(validator.validate(change, require_complete_tasks))
    return issues
