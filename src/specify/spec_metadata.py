"""读取和更新正式 spec 的可选元数据。"""

from pathlib import Path

from .config import dump_yaml, load_yaml
from .errors import SpecifyError


class SpecMetadata:
    """将索引使用的简介保存在正文之外。"""

    def __init__(self, spec_path: Path):
        """定位与 spec.md 同级的元数据文件。"""

        self.path = spec_path.with_name("meta-data.yaml")

    @staticmethod
    def normalize_description(value: object) -> str:
        """校验用于索引的一行简介，并去掉首尾空白。"""

        if (
            not isinstance(value, str)
            or not value.strip()
            or len(value.splitlines()) != 1
        ):
            raise SpecifyError("description 必须是一行非空文本")
        return value.strip()

    def description(self) -> str | None:
        """读取简介，兼容尚未创建元数据文件的 spec。"""

        if not self.path.is_file():
            return None
        data = load_yaml(self.path)
        if "description" not in data:
            return None
        try:
            return self.normalize_description(data["description"])
        except SpecifyError as error:
            raise SpecifyError(error.message, path=str(self.path)) from error

    def write_description(self, description: str) -> None:
        """只更新简介字段，保留文件已有的其他元数据。"""

        data = load_yaml(self.path) if self.path.is_file() else {}
        data["description"] = description
        dump_yaml(self.path, data)
