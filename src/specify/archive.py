"""change 归档与 append-only manifest 校验。"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import dump_yaml, load_config
from .contract import ContractIdentity
from .errors import SpecifyError
from .io import atomic_json, sha256_file
from .models import Change, Issue
from .paths import RepoPaths
from .validate.changes import ChangeValidator, read_metadata


class ArchiveService:
    """只封存已同步的 change，不负责也不会重放 delta。"""

    def __init__(self, paths: RepoPaths):
        """绑定项目路径，后续归档和 manifest 使用同一根目录。"""

        self.paths = paths
        self.manifest_path = paths.changes / "archived" / "manifest.json"

    def archive(self, change: Change) -> Path:
        """校验完成状态和 sync 回执，再移动 change 并登记文件 hash。"""

        if change.status != "implemented":
            raise SpecifyError("只有 implemented change 可以归档")

        config = load_config(self.paths)
        issues = ChangeValidator(self.paths, config).validate(
            change, require_complete_tasks=True
        )
        if issues:
            raise SpecifyError(issues[0].message, path=issues[0].path)

        metadata = read_metadata(change)
        self._require_current_sync_receipt(change, metadata)
        manifest = self._read_manifest()
        existing_issues = ArchiveValidator(self.paths).validate()
        if existing_issues:
            raise SpecifyError(existing_issues[0].message, path=existing_issues[0].path)
        metadata["updatedAt"] = (
            datetime.now().astimezone().isoformat(timespec="seconds")
        )
        dump_yaml(change.path / "meta-data.yaml", metadata)
        destination = self._archive_directory(change)
        self._append_manifest(change, destination, manifest)
        return destination

    def archived_at(self, change: Change) -> str | None:
        """从该 change 的元数据登记项读取归档时间。"""

        path = (change.path / "meta-data.yaml").relative_to(self.manifest_path.parent)
        for entry in self._read_manifest()["entries"]:
            if isinstance(entry, dict) and entry.get("path") == path.as_posix():
                value = entry.get("archivedAt")
                return value if isinstance(value, str) else None
        return None

    def _require_current_sync_receipt(
        self, change: Change, metadata: dict[str, Any]
    ) -> None:
        """有正式 spec delta 的 change 必须已有覆盖全部 delta 的当前回执。"""

        if "specImpact" in metadata:
            return
        receipt = metadata.get("sync")
        if not isinstance(receipt, dict):
            raise SpecifyError("归档前必须先成功 sync")

        current_hashes: dict[str, str] = {}
        for path in sorted((change.path / "deltas").glob("*/*.md")):
            relative = path.relative_to(change.path / "deltas").as_posix()
            current_hashes[relative] = ContractIdentity.file_hash(path.read_bytes())
        if receipt.get("deltaHashes") != current_hashes:
            raise SpecifyError("sync 回执与当前 delta 不一致，不能归档")

    def _archive_directory(self, change: Change) -> Path:
        """按日期移动 change，保留 kind 与 ID 目录层级。"""

        date = datetime.now().astimezone().strftime("%Y-%m-%d")
        destination = (
            self.paths.changes / "archived" / change.kind / f"{date}-{change.id}"
        )
        if destination.exists():
            raise SpecifyError(f"归档目标目录已存在：{destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(change.path), str(destination))
        return destination

    def _append_manifest(
        self, change: Change, directory: Path, manifest: dict[str, Any]
    ) -> None:
        """计算归档目录文件 hash，并按稳定顺序追加 manifest 记录。"""

        archived_at = datetime.now().astimezone().isoformat(timespec="seconds")
        archive_root = self.paths.changes / "archived"
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            manifest["entries"].append(
                {
                    "path": path.relative_to(archive_root).as_posix(),
                    "sha256": sha256_file(path),
                    "id": change.id,
                    "kind": change.kind,
                    "archivedAt": archived_at,
                }
            )
        manifest["entries"].sort(key=lambda item: (item["archivedAt"], item["path"]))
        atomic_json(self.manifest_path, manifest)

    def _read_manifest(self) -> dict[str, Any]:
        """读取 manifest；首次归档时建立空版本化清单。"""

        if not self.manifest_path.is_file():
            return {"version": 1, "entries": []}
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SpecifyError(
                f"archive manifest 格式错误：{exc}", path=str(self.manifest_path)
            ) from exc
        if (
            not isinstance(manifest, dict)
            or manifest.get("version") != 1
            or not isinstance(manifest.get("entries"), list)
        ):
            raise SpecifyError(
                "archive manifest 结构无效", path=str(self.manifest_path)
            )
        return manifest


class ArchiveValidator:
    """比较 archive manifest 与磁盘文件的集合和内容 hash。"""

    def __init__(self, paths: RepoPaths):
        """保存归档根目录和 manifest 路径。"""

        self.root = paths.changes / "archived"
        self.manifest_path = self.root / "manifest.json"

    def validate(self) -> list[Issue]:
        """报告 manifest 缺项、磁盘游离文件和内容篡改。"""

        if not self.manifest_path.is_file():
            unregistered = (
                sorted(
                    path.relative_to(self.root).as_posix()
                    for path in self.root.rglob("*")
                    if path.is_file()
                )
                if self.root.is_dir()
                else []
            )
            return [Issue("归档文件未登记到 manifest", name) for name in unregistered]
        try:
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return [Issue(f"archive manifest 格式错误：{exc}", str(self.manifest_path))]
        if (
            not isinstance(manifest, dict)
            or manifest.get("version") != 1
            or not isinstance(manifest.get("entries"), list)
        ):
            return [Issue("archive manifest 结构无效", str(self.manifest_path))]

        entries = manifest["entries"]
        if any(
            not isinstance(item, dict) or not isinstance(item.get("path"), str)
            for item in entries
        ):
            return [Issue("archive manifest 中存在无效条目", str(self.manifest_path))]
        registered = {item["path"]: item for item in entries}
        if len(registered) != len(entries):
            return [Issue("archive manifest 中有重复路径", str(self.manifest_path))]
        on_disk = {
            path.relative_to(self.root).as_posix(): path
            for path in self.root.rglob("*")
            if path.is_file() and path != self.manifest_path
        }
        issues: list[Issue] = []
        for name in sorted(set(registered) - set(on_disk)):
            issues.append(Issue("manifest 中登记的文件在磁盘上缺失", name))
        for name in sorted(set(on_disk) - set(registered)):
            issues.append(Issue("归档文件未登记到 manifest", name))
        for name in sorted(set(registered) & set(on_disk)):
            if sha256_file(on_disk[name]) != registered[name].get("sha256"):
                issues.append(Issue("归档文件 hash 不匹配", name))
        return issues


def archive_change(paths: RepoPaths, change: Change) -> Path:
    """提供给 CLI 的归档入口；此操作不会运行 sync。"""

    return ArchiveService(paths).archive(change)


def validate_archived(paths: RepoPaths) -> list[Issue]:
    """提供给 validate 命令的归档完整性入口。"""

    return ArchiveValidator(paths).validate()
