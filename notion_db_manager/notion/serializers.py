from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from notion_db_manager.constants import ORDER_PROPERTY, READONLY_PROPERTY_TYPES, SUPPORTED_WRITE_TYPES
from notion_db_manager.exceptions import NotionAPIError
from notion_db_manager.models import DatabaseContext


def serialize_page(
    page: dict[str, Any],
    index: int,
    selected_columns: list[str] | None = None,
) -> dict[str, Any]:
    properties = page["properties"]
    if selected_columns is None:
        selected_columns = [name for name in properties.keys() if name != ORDER_PROPERTY]
    serialized: dict[str, Any] = {}
    for name in selected_columns:
        if name in properties:
            serialized[name] = serialize_property(properties[name])
    return {
        "index": index,
        "page_id": page["id"],
        "properties": serialized,
    }


def serialize_property(property_value: dict[str, Any]) -> dict[str, Any]:
    property_type = property_value["type"]
    body = property_value[property_type]
    readonly = property_type in READONLY_PROPERTY_TYPES
    if property_type in {"title", "rich_text"}:
        value: Any = rich_text_to_plain_text(body)
    elif property_type == "number":
        value = body
    elif property_type in {"select", "status"}:
        value = body["name"] if body else None
    elif property_type == "multi_select":
        value = [item["name"] for item in body]
    elif property_type in {"checkbox", "date", "url", "email", "phone_number"}:
        value = body
    elif property_type in {"people", "relation"}:
        value = [item["id"] for item in body]
    elif property_type == "files":
        value = [serialize_file_item(item) for item in body]
    elif property_type == "formula":
        value = body[body["type"]]
    elif property_type == "rollup":
        value = [serialize_property(item) for item in body["array"]] if body["type"] == "array" else body[body["type"]]
    elif property_type in {"created_time", "last_edited_time", "unique_id", "verification"}:
        value = body
    elif property_type in {"created_by", "last_edited_by"}:
        value = body.get("id") if body else None
    else:
        value = body
        readonly = True
    result = {"type": property_type, "value": value}
    if readonly:
        result["readonly"] = True
    return result


def deserialize_properties(
    normalized_properties: dict[str, Any],
    schema: dict[str, dict[str, Any]],
    *,
    include_missing_writable_as_empty: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if include_missing_writable_as_empty:
        for name, config in schema.items():
            property_type = config["type"]
            if property_type in SUPPORTED_WRITE_TYPES:
                payload[name] = empty_property_value(property_type)

    for name, normalized in normalized_properties.items():
        if name not in schema:
            continue
        property_type = schema[name]["type"]
        if property_type in READONLY_PROPERTY_TYPES or property_type not in SUPPORTED_WRITE_TYPES:
            continue
        payload[name] = normalized_to_notion_value(property_type, normalized.get("value"))
    return payload


def build_export_document(
    context: DatabaseContext,
    rows: list[dict[str, Any]],
    export_type: str,
    selected_columns: list[str] | None = None,
    selected_rows: list[int] | None = None,
) -> dict[str, Any]:
    return {
        "meta": {
            "database_id": context.database_id,
            "database_name": context.database_name,
            "export_type": export_type,
            "selected_columns": selected_columns or [],
            "selected_rows": selected_rows or [],
            "order_property": context.order_property,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        },
        "rows": rows,
    }


def empty_property_value(property_type: str) -> dict[str, Any]:
    if property_type in {"title", "rich_text"}:
        return {property_type: []}
    if property_type == "number":
        return {"number": None}
    if property_type in {"select", "status"}:
        return {property_type: None}
    if property_type == "multi_select":
        return {"multi_select": []}
    if property_type == "checkbox":
        return {"checkbox": False}
    if property_type == "date":
        return {"date": None}
    if property_type in {"url", "email", "phone_number"}:
        return {property_type: None}
    if property_type in {"people", "relation", "files"}:
        return {property_type: []}
    raise NotionAPIError(f"不支援清空欄位型別: {property_type}")


def normalized_to_notion_value(property_type: str, value: Any) -> dict[str, Any]:
    if property_type in {"title", "rich_text"}:
        return {property_type: build_rich_text_array(value)}
    if property_type == "number":
        return {"number": value}
    if property_type in {"select", "status"}:
        return {property_type: {"name": value} if value is not None else None}
    if property_type == "multi_select":
        return {"multi_select": [{"name": item} for item in (value or [])]}
    if property_type == "checkbox":
        return {"checkbox": bool(value)}
    if property_type == "date":
        return {"date": value}
    if property_type in {"url", "email", "phone_number"}:
        return {property_type: value}
    if property_type == "people":
        return {"people": [{"id": item} for item in (value or [])]}
    if property_type == "relation":
        return {"relation": [{"id": item} for item in (value or [])]}
    if property_type == "files":
        files = []
        for item in value or []:
            files.append(
                {
                    "name": item.get("name") or item["url"],
                    "type": "external",
                    "external": {"url": item["url"]},
                }
            )
        return {"files": files}
    raise NotionAPIError(f"不支援寫入欄位型別: {property_type}")


def build_rich_text_array(value: Any) -> list[dict[str, Any]]:
    if value in (None, ""):
        return []
    if not isinstance(value, str):
        value = str(value)
    chunks = [value[index : index + 1900] for index in range(0, len(value), 1900)]
    return [{"type": "text", "text": {"content": chunk}} for chunk in chunks]


def rich_text_to_plain_text(items: list[dict[str, Any]]) -> str:
    return "".join(item.get("plain_text", "") for item in items)


def serialize_file_item(item: dict[str, Any]) -> dict[str, Any]:
    file_type = item["type"]
    return {
        "name": item.get("name"),
        "type": file_type,
        "url": item[file_type]["url"],
    }