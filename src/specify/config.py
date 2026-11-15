"""加载并校验 Specify 项目配置。"""

from __future__ import annotations

import re
from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from .errors import EnvironmentError, SpecifyError, require
from .io import atomic_write
from .paths import RepoPaths

KEY_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED_TOP = {"specTypes", "kinds"}


def load_yaml(path: Path) -> dict[str, Any]:
    """读取 YAML 映射，并把缺文件和语法错误转成项目错误。"""

    if not path.is_file():
        raise EnvironmentError("文件不存在", str(path))
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SpecifyError(f"YAML 格式无效：{exc}", path=path.as_posix()) from exc
    if not isinstance(data, dict):
        raise SpecifyError("YAML 文档必须是映射", path=path.as_posix())
    return dict(data)


def validate_config(data: dict[str, Any]) -> dict[str, Any]:
    """校验 init.yaml 与 spec/config.yaml 共用的固定字段结构。"""

    unknown = set(data) - ALLOWED_TOP
    require(not unknown, f"配置包含未知字段：{', '.join(sorted(unknown))}")
    for section in ALLOWED_TOP:
        values = data.get(section)
        require(isinstance(values, dict) and values, f"{section} 必须是非空映射")
        for key, value in values.items():
            require(
                isinstance(key, str) and KEY_RE.fullmatch(key),
                f"{section} 中的 key 无效：{key}",
            )
            require(isinstance(value, dict), f"{section}.{key} 必须是映射")
            allowed_item_fields = {"label", "description"}
            if section == "specTypes":
                allowed_item_fields.add("template")
            unknown_item_fields = set(value) - allowed_item_fields
            require(
                not unknown_item_fields,
                f"{section}.{key} 有未知字段：{', '.join(sorted(unknown_item_fields))}",
            )
            require(
                isinstance(value.get("label"), str) and value["label"].strip(),
                f"{section}.{key}.label 必填",
            )
            require(
                isinstance(value.get("description"), str)
                and value["description"].strip(),
                f"{section}.{key}.description 必填",
            )
            if section == "specTypes" and "template" in value:
                template = value["template"]
                template_parts = (
                    Path(template).parts if isinstance(template, str) else ()
                )
                require(
                    isinstance(template, str)
                    and template.endswith(".md")
                    and not Path(template).is_absolute()
                    and ".." not in template_parts
                    and template_parts[0] == "template",
                    f"specTypes.{key}.template 必须指向 spec/template/ 下的 Markdown 文件",
                )
    return data


def load_config(paths: RepoPaths) -> dict[str, Any]:
    """读取并校验已初始化项目的正式配置。"""

    return validate_config(load_yaml(paths.require_config()))


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    """用稳定字段顺序序列化 YAML，再原子替换目标文件。"""

    yaml = YAML()
    yaml.default_flow_style = False
    buffer = StringIO()
    yaml.dump(data, buffer)
    atomic_write(path, buffer.getvalue())
