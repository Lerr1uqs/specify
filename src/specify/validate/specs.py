"""formal spec 树的遍历与验证。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..errors import SpecifyError
from ..models import Issue, SpecDocument
from ..parse.spec import SpecParser
from ..paths import RepoPaths, validate_id
from ..references import ContractLinks


class SpecTreeValidator:
    """只读取配置声明的 formal spec，并逐份校验 Markdown。"""

    def __init__(self, paths: RepoPaths, config: dict[str, Any]):
        """缓存正式 spec 根目录和允许的类型集合。"""

        self.paths = paths
        self.config = config
        self.parser = SpecParser()

    def files(self) -> list[Path]:
        """返回类型和 spec ID 排序后的正式 spec.md 文件。"""

        result: list[Path] = []
        for spec_type in sorted(self.config["specTypes"]):
            base = self.paths.specs / spec_type
            if not base.is_dir():
                continue
            for spec_dir in sorted(base.iterdir()):
                candidate = spec_dir / "spec.md"
                if candidate.is_file():
                    result.append(candidate)
        return result

    def validate(self) -> list[Issue]:
        """收集所有 formal spec 中的首个结构或内容错误。"""

        issues: list[Issue] = []
        documents: dict[Path, SpecDocument] = {}
        for path in self.files():
            if not validate_id(path.parent.name):
                issues.append(
                    Issue("spec id 必须为 kebab-case", path.parent.as_posix())
                )
            try:
                documents[path] = self.parser.parse_file(path)
            except SpecifyError as exc:
                issues.append(Issue(exc.message, str(exc.path or path)))
        # 格式问题修复后再核对完整图，避免一次坏文件被误报成多个悬挂引用。
        return issues or ContractLinks(documents).validate()


def formal_spec_files(paths: RepoPaths, config: dict[str, Any]) -> list[Path]:
    """提供其他模块使用的 formal spec 文件列表。"""

    return SpecTreeValidator(paths, config).files()


def validate_specs(paths: RepoPaths, config: dict[str, Any]) -> list[Issue]:
    """校验所有 formal spec，索引与 CLI 复用同一遍历规则。"""

    return SpecTreeValidator(paths, config).validate()
