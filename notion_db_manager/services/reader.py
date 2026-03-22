from __future__ import annotations

from notion_db_manager.json_storage import write_json_file
from notion_db_manager.notion.client import NotionClient
from notion_db_manager.notion.serializers import build_export_document, serialize_page
from notion_db_manager.services.validation import parse_index_list, validate_columns


class ReaderService:
    def export_all(self, client: NotionClient, context, output_path: str) -> int:
        pages = client.get_ordered_pages(context)
        rows = [serialize_page(page, index=index) for index, page in enumerate(pages, start=1)]
        write_json_file(output_path, build_export_document(context, rows, export_type="full"))
        return len(rows)

    def export_columns(self, client: NotionClient, context, output_path: str, columns: list[str]) -> int:
        validate_columns(columns, context)
        pages = client.get_ordered_pages(context)
        rows = [serialize_page(page, index=index, selected_columns=columns) for index, page in enumerate(pages, start=1)]
        write_json_file(output_path, build_export_document(context, rows, export_type="columns", selected_columns=columns))
        return len(rows)

    def export_rows(self, client: NotionClient, context, output_path: str, row_expression: str) -> int:
        selected_rows = parse_index_list(row_expression)
        pages = client.get_ordered_pages(context)
        rows = []
        for row_index in selected_rows:
            if row_index > len(pages):
                from notion_db_manager.exceptions import NotionAPIError

                raise NotionAPIError(f"指定 row index {row_index} 超出目前資料筆數 {len(pages)}")
            rows.append(serialize_page(pages[row_index - 1], index=row_index))
        write_json_file(output_path, build_export_document(context, rows, export_type="rows", selected_rows=selected_rows))
        return len(rows)