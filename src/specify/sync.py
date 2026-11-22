"""执行 spec delta 的预检、合并与同步回执写入。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import dump_yaml, load_config
from .contract import ContractIdentity
from .errors import SpecifyError
from .history import ContractHistory
from .index import build_index
from .io import atomic_write, move_to_trash
from .merge import DeltaMerger
from .models import Change, SpecDocument
from .parse.delta import parse_delta_file
from .parse.spec import parse_spec_file, render_spec
from .paths import RepoPaths
from .validate.changes import ChangeValidator, read_metadata


class SpecSynchronizer:
    """将一个 implemented change 的 delta 写入正式 spec。"""

    def __init__(self, paths: RepoPaths):
        """初始化项目路径和确定性的 delta 合并器。"""

        self.paths = paths
        self.merger = DeltaMerger()

    def sync(self, change: Change) -> bool:
        """完成预检后同步所有目标；已有相同回执时直接返回 False。"""

        if change.status != "implemented":
            raise SpecifyError("只有 implemented change 可以 sync")
        metadata = read_metadata(change)
        config = load_config(self.paths)
        issues = ChangeValidator(self.paths, config).validate(change)
        if issues:
            raise SpecifyError(issues[0].message, path=issues[0].path)
        if "specImpact" in metadata:
            return False

        delta_paths = sorted((change.path / "deltas").glob("*/*.md"))
        delta_hashes = {
            path.relative_to(
                change.path / "deltas"
            ).as_posix(): ContractIdentity.file_hash(path.read_bytes())
            for path in delta_paths
        }
        if metadata.get("sync"):
            # 校验器已确认回执与 delta 相同，不能再把 delta 重放到 spec。
            return False

        prepared = self._prepare_spec_updates(change, metadata)

        # 回执写成前保留新旧快照；失败或中断的记录不会被查询发布。
        applied_at = datetime.now().astimezone()
        history_id = uuid4().hex
        ContractHistory(self.paths).stage_sync(
            change.id, history_id, applied_at, prepared
        )

        # 所有 delta 已在内存中通过基线和目标检查，之后才开始写正式 spec。
        for spec_path, (_, updated) in prepared.items():
            if updated.contracts:
                atomic_write(spec_path, render_spec(updated))
            else:
                move_to_trash(spec_path.parent, self.paths.root)

        # 索引也是 sync 的派生结果，确认它更新成功后才写成功回执。
        build_index(self.paths, config)
        timestamp = applied_at.isoformat(timespec="seconds")
        metadata["updatedAt"] = timestamp
        metadata["sync"] = {
            "appliedAt": timestamp,
            "deltaHashes": delta_hashes,
            "historyId": history_id,
        }
        dump_yaml(change.path / "meta-data.yaml", metadata)
        return True

    def _prepare_spec_updates(
        self, change: Change, metadata: dict[str, Any]
    ) -> dict[Path, tuple[SpecDocument, SpecDocument]]:
        """在内存中合并每个 spec，返回各目标的同步前后内容。"""

        prepared: dict[Path, tuple[SpecDocument, SpecDocument]] = {}
        for target in metadata["affects"]:
            spec_type, spec_id = target["type"], target["id"]
            spec_dir = self.paths.specs / spec_type / spec_id
            spec_path = spec_dir / "spec.md"
            delta_path = change.path / "deltas" / spec_type / f"{spec_id}.md"

            current = (
                parse_spec_file(spec_path) if spec_path.is_file() else SpecDocument()
            )
            updated = self.merger.apply(current, parse_delta_file(delta_path))
            prepared[spec_path] = current, updated
        return prepared


def sync_change(paths: RepoPaths, change: Change) -> bool:
    """提供给 CLI 的同步入口，实际流程由 SpecSynchronizer 负责。"""

    return SpecSynchronizer(paths).sync(change)
