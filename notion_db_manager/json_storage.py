from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from notion_db_manager.paths import resolve_input_path, resolve_output_path


def read_json_file(path: str) -> dict[str, Any]:
    input_path = resolve_input_path(path)
    if not input_path.is_file():
        raise FileNotFoundError(
            f"找不到 JSON 檔案: {path} (已檢查 {input_path})"
        )
    with input_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json_file(path: str, data: dict[str, Any]) -> Path:
    output_path = resolve_output_path(path)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    return output_path