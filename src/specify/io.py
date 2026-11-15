"""原子写入、hash 和可恢复移动等文件操作。"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    """先写同目录临时文件，再原子替换目标文本文件。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary, path)
    except Exception:
        # 写入失败的临时文件移入项目 .trash，保留现场供人工检查。
        if os.path.exists(temporary):
            trash = path.parent / ".trash"
            trash.mkdir(parents=True, exist_ok=True)
            os.replace(temporary, trash / Path(temporary).name)
        raise


def atomic_json(path: Path, value: object) -> None:
    """按稳定键顺序生成 JSON，并复用文本原子写入。"""

    atomic_write(
        path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def sha256_file(path: Path) -> str:
    """分块计算文件 SHA-256，避免一次读入大型归档文件。"""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def move_to_trash(path: Path, root: Path) -> Path:
    """把要移除的项目内容移到根目录 .trash 下以便人工恢复。"""

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    trash = root / ".trash" / timestamp
    trash.mkdir(parents=True)
    destination = trash / path.name
    os.replace(path, destination)
    return destination
