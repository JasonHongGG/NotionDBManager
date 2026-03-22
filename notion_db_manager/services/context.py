from __future__ import annotations

from argparse import Namespace

from notion_db_manager.env import get_env_value, load_env_file
from notion_db_manager.models import DatabaseContext
from notion_db_manager.notion.client import NotionClient


class ContextResolver:
    def resolve(self, args: Namespace, ensure_order_property: bool = True) -> tuple[NotionClient, DatabaseContext]:
        load_env_file()
        token = args.token or get_env_value("token") or input("Notion token: ").strip()
        database_name = args.database_name or get_env_value("database_name") or input("Database name: ").strip()
        client = NotionClient(token)
        context = client.search_database_by_name(database_name)
        if ensure_order_property:
            context = client.ensure_order_property(context)
        return client, context