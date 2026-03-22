from __future__ import annotations

import json
from typing import Any

import requests

from notion_db_manager.constants import NOTION_VERSION, ORDER_PROPERTY
from notion_db_manager.exceptions import NotionAPIError
from notion_db_manager.models import DatabaseContext


class NotionClient:
    def __init__(self, token: str) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Notion-Version": NOTION_VERSION,
            }
        )

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.request(
            method=method,
            url=f"https://api.notion.com/v1{path}",
            json=payload,
            timeout=30,
        )
        if response.status_code >= 400:
            try:
                body = response.json()
            except json.JSONDecodeError:
                body = {"message": response.text}
            raise NotionAPIError(f"Notion API {response.status_code}: {body.get('message', 'unknown error')}")
        if not response.content:
            return {}
        return response.json()

    def search_database_by_name(self, database_name: str) -> DatabaseContext:
        payload: dict[str, Any] = {
            "query": database_name,
            "filter": {"value": "database", "property": "object"},
            "page_size": 100,
        }
        matches: list[dict[str, Any]] = []
        while True:
            result = self._request("POST", "/search", payload)
            matches.extend(result.get("results", []))
            if not result.get("has_more"):
                break
            payload["start_cursor"] = result["next_cursor"]

        normalized_name = database_name.strip().lower()
        exact_matches = [item for item in matches if extract_database_title(item).strip().lower() == normalized_name]
        candidates = exact_matches or matches
        if not candidates:
            raise NotionAPIError(f"找不到名稱為 '{database_name}' 的資料庫")
        if len(candidates) > 1 and not exact_matches:
            names = ", ".join(extract_database_title(item) or item["id"] for item in candidates[:5])
            raise NotionAPIError(f"找到多個相近資料庫，請改用更精確名稱: {names}")
        return self.get_database_context(candidates[0]["id"])

    def get_database_context(self, database_id: str) -> DatabaseContext:
        database = self._request("GET", f"/databases/{database_id}")
        properties = database["properties"]
        title_property = next((name for name, config in properties.items() if config["type"] == "title"), None)
        if not title_property:
            raise NotionAPIError("資料庫缺少 title 欄位，無法建立或更新 page")
        return DatabaseContext(
            database_id=database["id"],
            database_name=extract_database_title(database) or database["id"],
            properties=properties,
            title_property=title_property,
            order_property=ORDER_PROPERTY,
        )

    def ensure_order_property(self, context: DatabaseContext) -> DatabaseContext:
        config = context.properties.get(context.order_property)
        if config and config["type"] != "number":
            raise NotionAPIError(
                f"資料庫中已存在 '{context.order_property}' 欄位，但型別不是 number，請手動更名或移除"
            )
        if not config:
            self._request(
                "PATCH",
                f"/databases/{context.database_id}",
                {"properties": {context.order_property: {"number": {}}}},
            )
            context = self.get_database_context(context.database_id)

        pages = self.query_pages(context.database_id, sorts=[{"timestamp": "created_time", "direction": "ascending"}])
        for index, page in enumerate(pages, start=1):
            current = page["properties"].get(context.order_property, {}).get("number")
            if current != index:
                self.update_page(page["id"], {context.order_property: {"number": index}})
        return self.get_database_context(context.database_id)

    def query_pages(self, database_id: str, sorts: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"page_size": 100}
        if sorts:
            payload["sorts"] = sorts
        results: list[dict[str, Any]] = []
        while True:
            response = self._request("POST", f"/databases/{database_id}/query", payload)
            results.extend(response.get("results", []))
            if not response.get("has_more"):
                break
            payload["start_cursor"] = response["next_cursor"]
        return results

    def get_ordered_pages(self, context: DatabaseContext) -> list[dict[str, Any]]:
        return self.query_pages(
            context.database_id,
            sorts=[
                {"property": context.order_property, "direction": "ascending"},
                {"timestamp": "created_time", "direction": "ascending"},
            ],
        )

    def update_page(self, page_id: str, properties: dict[str, Any], archived: bool | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"properties": properties}
        if archived is not None:
            payload["archived"] = archived
        return self._request("PATCH", f"/pages/{page_id}", payload)

    def create_page(self, database_id: str, properties: dict[str, Any]) -> dict[str, Any]:
        payload = {"parent": {"database_id": database_id}, "properties": properties}
        return self._request("POST", "/pages", payload)

    def archive_pages(self, page_ids: list[str]) -> None:
        for page_id in page_ids:
            self.update_page(page_id, {}, archived=True)


def extract_database_title(database: dict[str, Any]) -> str:
    title_items = database.get("title", [])
    return "".join(item.get("plain_text", "") for item in title_items)