from __future__ import annotations

from typing import Any

from notion_db_manager.exceptions import NotionAPIError
from notion_db_manager.json_storage import read_json_file
from notion_db_manager.models import DatabaseContext
from notion_db_manager.notion.client import NotionClient
from notion_db_manager.notion.serializers import deserialize_properties
from notion_db_manager.services.validation import validate_columns


class WriterService:
    def import_full(self, client: NotionClient, context: DatabaseContext, input_path: str, mode: str) -> int:
        document = read_json_file(input_path)
        rows = document.get("rows", [])
        existing_pages = client.get_ordered_pages(context)
        start_index = 1
        if mode == "replace":
            client.archive_pages([page["id"] for page in existing_pages])
        else:
            start_index = len(existing_pages) + 1

        for offset, row in enumerate(rows):
            client.create_page(context.database_id, self.build_full_row_payload(row, context, start_index + offset))
        return len(rows)

    def write_columns(self, client: NotionClient, context: DatabaseContext, input_path: str, start_index: int) -> int:
        if start_index <= 0:
            raise NotionAPIError("start-index 需從 1 開始")
        document = read_json_file(input_path)
        rows = document.get("rows", [])
        existing_pages = client.get_ordered_pages(context)
        if start_index > len(existing_pages) + 1:
            raise NotionAPIError(f"start-index 最多只能到 {len(existing_pages) + 1}")

        for offset, row in enumerate(rows):
            target_index = start_index + offset
            properties = row.get("properties", {})
            validate_columns(list(properties.keys()), context)
            partial_payload = deserialize_properties(properties, context.properties)
            partial_payload[context.order_property] = {"number": target_index}
            if target_index <= len(existing_pages):
                client.update_page(existing_pages[target_index - 1]["id"], partial_payload)
            else:
                client.create_page(context.database_id, self.with_required_defaults(partial_payload, context, target_index))
        return len(rows)

    def write_rows(self, client: NotionClient, context: DatabaseContext, input_path: str, mode: str, index: int | None) -> int:
        document = read_json_file(input_path)
        rows = document.get("rows", [])
        existing_pages = client.get_ordered_pages(context)

        if mode == "append":
            start_index = len(existing_pages) + 1
            for offset, row in enumerate(rows):
                client.create_page(context.database_id, self.build_full_row_payload(row, context, start_index + offset))
            return len(rows)

        if index is None or index <= 0:
            raise NotionAPIError("insert 與 overwrite 模式需要提供 --index，且需從 1 開始")

        if mode == "insert":
            if index > len(existing_pages) + 1:
                raise NotionAPIError(f"insert index 最多只能到 {len(existing_pages) + 1}")
            shift_count = len(rows)
            for page in reversed(existing_pages[index - 1 :]):
                current_order = page["properties"][context.order_property]["number"]
                client.update_page(page["id"], {context.order_property: {"number": current_order + shift_count}})
            for offset, row in enumerate(rows):
                client.create_page(context.database_id, self.build_full_row_payload(row, context, index + offset))
            return len(rows)

        required_count = index - 1 + len(rows)
        if required_count > len(existing_pages):
            raise NotionAPIError(
                f"overwrite 需要覆蓋的 row 超出現有資料筆數，至少需要 {required_count} 筆，目前只有 {len(existing_pages)} 筆"
            )
        for offset, row in enumerate(rows):
            page = existing_pages[index - 1 + offset]
            payload = self.build_full_row_payload(
                row,
                context,
                page["properties"][context.order_property]["number"],
                erase_existing=True,
            )
            client.update_page(page["id"], payload)
        return len(rows)

    def build_full_row_payload(
        self,
        row: dict[str, Any],
        context: DatabaseContext,
        index: int,
        erase_existing: bool = False,
    ) -> dict[str, Any]:
        properties = row.get("properties", {})
        payload = deserialize_properties(
            properties,
            context.properties,
            include_missing_writable_as_empty=erase_existing,
        )
        payload[context.order_property] = {"number": index}
        return self.with_required_defaults(payload, context, index)

    def with_required_defaults(
        self,
        payload: dict[str, Any],
        context: DatabaseContext,
        index: int,
    ) -> dict[str, Any]:
        if context.title_property not in payload:
            payload[context.title_property] = {"title": []}
        if context.order_property not in payload:
            payload[context.order_property] = {"number": index}
        return payload