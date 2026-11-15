"""项目路径与基于目录的 change 生命周期定位。"""

from __future__ import annotations

import re
from pathlib import Path

from .errors import EnvironmentError, SpecifyError
from .models import Change

DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-(.+)$")
ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STATUSES = ("proposed", "implemented", "rejected", "archived")


class RepoPaths:
    """集中解析项目目录，避免业务代码自行拼接路径。"""

    def __init__(self, root: Path):
        """解析项目根目录并缓存常用路径。"""

        self.root = root.resolve()
        self.spec = self.root / "spec"
        self.config = self.spec / "config.yaml"
        self.specs = self.spec / "specs"
        self.templates = self.spec / "template"
        self.changes = self.spec / "changes"
        self.index = self.spec / "spec-index.md"

    def require_config(self) -> Path:
        """要求当前目录已初始化为 Specify 项目。"""

        if not self.config.is_file():
            raise EnvironmentError(
                "项目尚未初始化，缺少 spec/config.yaml", str(self.config)
            )
        return self.config


class ChangeTree:
    """扫描并解析 changes 下的全局唯一 change ID。"""

    def __init__(self, paths: RepoPaths):
        """绑定 changes 根路径。"""

        self.paths = paths

    def scan(self) -> list[Change]:
        """按状态和 kind 排序遍历 change 目录，拒绝重复 ID。"""

        changes: list[Change] = []
        locations: dict[str, Path] = {}
        for status in STATUSES:
            base = self.paths.changes / status
            if not base.is_dir():
                continue
            for kind_dir in sorted(base.iterdir()):
                if not kind_dir.is_dir():
                    continue
                for change_dir in sorted(kind_dir.iterdir()):
                    if not change_dir.is_dir():
                        continue
                    change_id = self._directory_id(status, change_dir.name)
                    if change_id in locations:
                        raise SpecifyError(
                            f"change id 重复：{change_id} 位于 {locations[change_id]} 和 {change_dir}"
                        )
                    locations[change_id] = change_dir
                    changes.append(Change(change_id, kind_dir.name, status, change_dir))
        return changes

    def find(self, change_id: str) -> Change:
        """按全局 ID 返回唯一 change；不存在时报告环境错误。"""

        for change in self.scan():
            if change.id == change_id:
                return change
        raise EnvironmentError(f"找不到 change：{change_id}")

    @staticmethod
    def _directory_id(status: str, name: str) -> str:
        """仅对 archived 目录去除日期前缀。"""

        if status != "archived":
            return name
        match = DATE_PREFIX.fullmatch(name)
        return match.group(1) if match else name


def validate_id(value: str) -> bool:
    """判断 spec/change/Contract ID 是否符合 kebab-case 协议。"""

    return bool(ID_PATTERN.fullmatch(value))


def scan_changes(paths: RepoPaths) -> list[Change]:
    """提供简单扫描入口，实际目录遍历由 ChangeTree 负责。"""

    return ChangeTree(paths).scan()


def find_change(paths: RepoPaths, change_id: str) -> Change:
    """提供简单查找入口，实际定位由 ChangeTree 负责。"""

    return ChangeTree(paths).find(change_id)
