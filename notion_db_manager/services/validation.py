from __future__ import annotations

from notion_db_manager.exceptions import NotionAPIError
from notion_db_manager.models import DatabaseContext


def parse_index_list(raw: str) -> list[int]:
    result: set[int] = set()
    for chunk in [part.strip() for part in raw.split(",") if part.strip()]:
        if "-" in chunk:
            start_text, end_text = chunk.split("-", 1)
            start = int(start_text)
            end = int(end_text)
            if start <= 0 or end <= 0 or end < start:
                raise ValueError(f"無效索引區間: {chunk}")
            result.update(range(start, end + 1))
        else:
            value = int(chunk)
            if value <= 0:
                raise ValueError(f"索引需從 1 開始: {chunk}")
            result.add(value)
    return sorted(result)


def validate_columns(columns: list[str], context: DatabaseContext) -> None:
    invalid = [column for column in columns if column not in context.properties]
    if invalid:
        raise NotionAPIError(f"找不到欄位: {', '.join(invalid)}")