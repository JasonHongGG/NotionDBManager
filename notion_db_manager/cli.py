from __future__ import annotations

import argparse
import json

from notion_db_manager.exceptions import NotionAPIError
from notion_db_manager.paths import resolve_input_path, resolve_output_path
from notion_db_manager.services.context import ContextResolver
from notion_db_manager.services.reader import ReaderService
from notion_db_manager.services.writer import WriterService


context_resolver = ContextResolver()
reader_service = ReaderService()
writer_service = WriterService()


def main() -> None:
	parser = build_parser()
	args = parser.parse_args()
	try:
		args.func(args)
	except NotionAPIError as error:
		raise SystemExit(str(error)) from error
	except ValueError as error:
		raise SystemExit(str(error)) from error
	except json.JSONDecodeError as error:
		raise SystemExit(f"JSON 格式錯誤: {error}") from error


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="Read and write Notion databases as JSON")
	subparsers = parser.add_subparsers(dest="category", required=True)

	reader = subparsers.add_parser("reader", help="Reader operations")
	reader_subparsers = reader.add_subparsers(dest="action", required=True)

	export_all = reader_subparsers.add_parser("export-all", help="Export all rows and all columns")
	add_common_database_args(export_all)
	export_all.add_argument("-o", "--output", required=True, help="Output JSON file path")
	export_all.set_defaults(func=handle_export_all)

	export_columns = reader_subparsers.add_parser("export-columns", help="Export only selected columns")
	add_common_database_args(export_columns)
	export_columns.add_argument("--columns", nargs="+", required=True, help="Column names to export")
	export_columns.add_argument("-o", "--output", required=True, help="Output JSON file path")
	export_columns.set_defaults(func=handle_export_columns)

	export_rows = reader_subparsers.add_parser("export-rows", help="Export only selected row indexes")
	add_common_database_args(export_rows)
	export_rows.add_argument("--rows", required=True, help="Row indexes, e.g. 1,3,5-7")
	export_rows.add_argument("-o", "--output", required=True, help="Output JSON file path")
	export_rows.set_defaults(func=handle_export_rows)

	writer = subparsers.add_parser("writer", help="Writer operations")
	writer_subparsers = writer.add_subparsers(dest="action", required=True)

	import_full = writer_subparsers.add_parser("import-full", help="Import JSON created by export-all")
	add_common_database_args(import_full)
	import_full.add_argument("--input", required=True, help="Input JSON file path")
	import_full.add_argument("--mode", choices=["append", "replace"], required=True, help="append or replace existing rows")
	import_full.set_defaults(func=handle_import_full)

	write_columns = writer_subparsers.add_parser("write-columns", help="Write partial column data from JSON")
	add_common_database_args(write_columns)
	write_columns.add_argument("--input", required=True, help="Input JSON file path")
	write_columns.add_argument("--start-index", type=int, default=1, help="Target row index, starts from 1")
	write_columns.set_defaults(func=handle_write_columns)

	write_rows = writer_subparsers.add_parser("write-rows", help="Append, insert, or overwrite whole rows")
	add_common_database_args(write_rows)
	write_rows.add_argument("--input", required=True, help="Input JSON file path")
	write_rows.add_argument("--mode", choices=["append", "insert", "overwrite"], required=True)
	write_rows.add_argument("--index", type=int, help="Required for insert and overwrite")
	write_rows.set_defaults(func=handle_write_rows)

	return parser


def add_common_database_args(parser: argparse.ArgumentParser) -> None:
	parser.add_argument("--token", help="Notion integration token; defaults to .env or environment variables")
	parser.add_argument("--database-name", help="Exact Notion database name; defaults to .env or environment variables")


def handle_export_all(args: argparse.Namespace) -> None:
	client, context = context_resolver.resolve(args)
	count = reader_service.export_all(client, context, args.output)
	print(f"已匯出 {count} 筆資料到 {resolve_output_path(args.output)}")


def handle_export_columns(args: argparse.Namespace) -> None:
	client, context = context_resolver.resolve(args)
	count = reader_service.export_columns(client, context, args.output, args.columns)
	print(f"已匯出 {count} 筆資料的指定欄位到 {resolve_output_path(args.output)}")


def handle_export_rows(args: argparse.Namespace) -> None:
	client, context = context_resolver.resolve(args)
	count = reader_service.export_rows(client, context, args.output, args.rows)
	print(f"已匯出 {count} 筆指定 row 到 {resolve_output_path(args.output)}")


def handle_import_full(args: argparse.Namespace) -> None:
	client, context = context_resolver.resolve(args)
	count = writer_service.import_full(client, context, args.input, args.mode)
	print(f"已從 {resolve_input_path(args.input)} 寫入 {count} 筆資料，模式: {args.mode}")


def handle_write_columns(args: argparse.Namespace) -> None:
	client, context = context_resolver.resolve(args)
	count = writer_service.write_columns(client, context, args.input, args.start_index)
	print(f"已從 {resolve_input_path(args.input)} 讀取資料，並自 index {args.start_index} 開始寫入 {count} 筆欄位資料")


def handle_write_rows(args: argparse.Namespace) -> None:
	client, context = context_resolver.resolve(args)
	count = writer_service.write_rows(client, context, args.input, args.mode, args.index)
	if args.mode == "append":
		print(f"已從 {resolve_input_path(args.input)} append {count} 筆 row")
	elif args.mode == "insert":
		print(f"已從 {resolve_input_path(args.input)} 讀取資料，並自 index {args.index} 插入 {count} 筆 row")
	else:
		print(f"已從 {resolve_input_path(args.input)} 讀取資料，並自 index {args.index} 開始覆蓋 {count} 筆 row")


__all__ = ["main"]
