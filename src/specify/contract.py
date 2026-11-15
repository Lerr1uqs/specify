"""Contract ID、标题规范化和正文版本规则。"""

from __future__ import annotations

import hashlib
import re
import unicodedata

CONTRACT_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ContractIdentity:
    """集中提供 CLI 共用的 Contract 标识处理。"""

    @staticmethod
    def is_valid_id(contract_id: str) -> bool:
        """检查 Contract 标题中显式使用的 kebab-case ID。"""

        return bool(CONTRACT_ID_PATTERN.fullmatch(contract_id))

    @staticmethod
    def normalize_title(title: str) -> str:
        """仅规范 Unicode 形式和空白，用于标题去重。"""

        return " ".join(unicodedata.normalize("NFKC", title).split())

    @staticmethod
    def body_hash(body: str) -> str:
        """规范化正文边缘空行后计算 hash，并保留内部 Markdown 内容。"""

        normalized = body.replace("\r\n", "\n").replace("\r", "\n")
        lines = normalized.split("\n")

        # 只有边缘空行不参与版本判断，内部格式变化仍反映在 hash 中。
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()

        return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()

    @staticmethod
    def file_hash(content: bytes) -> str:
        """按原始文件字节计算 sync 回执和归档清单使用的 hash。"""

        return hashlib.sha256(content).hexdigest()


# 保留短入口，让解析器和其他调用方无需接触服务类细节。
def normalize_title(title: str) -> str:
    """返回标题去重使用的规范化文本。"""

    return ContractIdentity.normalize_title(title)


def contract_body_hash(body: str) -> str:
    """返回一段已提取 Contract 正文的协议 hash。"""

    return ContractIdentity.body_hash(body)
