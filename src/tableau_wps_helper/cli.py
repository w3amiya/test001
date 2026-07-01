from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config, save_config
from .excel_writer import ExcelImportError, import_file_to_workbook
from .logger import log_path_for, setup_logger
from .tableau_automation import ExportRequest, TableauAutomation, TableauAutomationError, TableauAutomationUnavailable
from .twb_parser import TwbParseError, list_worksheets


def cmd_list_worksheets(args: argparse.Namespace) -> int:
    config = load_config()
    logger = setup_logger(config)
    try:
        worksheets = list_worksheets(args.twb)
        config.add_recent_twb(args.twb)
        save_config(config)
        result = [w.name for w in worksheets]
        logger.info("Listed worksheets twb=%s count=%s", args.twb, len(result))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except TwbParseError as exc:
        logger.error("List worksheets failed twb=%s error=%s", args.twb, exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_import_file(args: argparse.Namespace) -> int:
    config = load_config()
    logger = setup_logger(config)
    try:
        result = import_file_to_workbook(
            source_path=args.source,
            workbook_path=args.workbook,
            sheet_name=args.sheet,
            start_cell=args.start_cell,
            header_rows=args.header_rows,
        )
        logger.info(
            "Imported file source=%s workbook=%s sheet=%s rows=%s columns=%s",
            args.source,
            result.target_workbook,
            result.target_sheet,
            result.rows_written,
            result.columns_written,
        )
        print(json.dumps(result.__dict__, ensure_ascii=False, indent=2))
        return 0
    except ExcelImportError as exc:
        logger.error("Import failed source=%s workbook=%s sheet=%s error=%s", args.source, args.workbook, args.sheet, exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def cmd_show_config(args: argparse.Namespace) -> int:
    config = load_config()
    print(json.dumps(config.to_dict(), ensure_ascii=False, indent=2))
    return 0


def cmd_log_path(args: argparse.Namespace) -> int:
    config = load_config()
    print(log_path_for(config))
    return 0


def cmd_set_tableau_path(args: argparse.Namespace) -> int:
    config = load_config()
    config.tableau_desktop_path = str(Path(args.path).expanduser())
    save_config(config)
    print(json.dumps({"tableauDesktopPath": config.tableau_desktop_path}, ensure_ascii=False, indent=2))
    return 0


def cmd_set_mapping(args: argparse.Namespace) -> int:
    config = load_config()
    config.set_sheet_mapping(args.twb, args.worksheet, args.sheet)
    save_config(config)
    print(json.dumps({"twb": args.twb, "worksheet": args.worksheet, "sheet": args.sheet}, ensure_ascii=False, indent=2))
    return 0


def cmd_automation_status(args: argparse.Namespace) -> int:
    config = load_config()
    automation = TableauAutomation(config.tableau_desktop_path)
    print(json.dumps({
        "implemented": False,
        "tableauDesktopPath": config.tableau_desktop_path,
        "tableauDesktopPathExists": automation.is_available(),
        "message": "Tableau Desktop automation interface is reserved but not implemented yet."
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_export_tableau(args: argparse.Namespace) -> int:
    config = load_config()
    logger = setup_logger(config)
    automation = TableauAutomation(config.tableau_desktop_path)
    worksheets = [w.strip() for w in args.worksheet if w.strip()]
    request = ExportRequest(
        twb_path=args.twb,
        worksheets=worksheets,
        export_dir=args.export_dir or config.default_export_dir,
        export_format=args.format,
        refresh=not args.no_refresh,
        timeout_seconds=args.timeout_seconds or config.default_timeout_seconds,
        use_cache_on_refresh_failure=args.use_cache_on_refresh_failure,
    )
    try:
        exported = automation.export_worksheets(request)
        logger.info(
            "Tableau export succeeded twb=%s worksheets=%s files=%s",
            args.twb,
            worksheets,
            [item.file_path for item in exported],
        )
        print(json.dumps([item.__dict__ for item in exported], ensure_ascii=False, indent=2))
        return 0
    except (TableauAutomationUnavailable, TableauAutomationError) as exc:
        logger.error("Tableau export failed twb=%s worksheets=%s error=%s", args.twb, worksheets, exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tableau WPS local helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-worksheets", help="List worksheets from a .twb file")
    list_parser.add_argument("twb", help="Path to .twb file")
    list_parser.set_defaults(func=cmd_list_worksheets)

    import_parser = subparsers.add_parser("import-file", help="Import CSV/XLSX into an existing workbook sheet")
    import_parser.add_argument("--source", required=True, help="CSV/XLSX source file")
    import_parser.add_argument("--workbook", required=True, help="Target .xlsx workbook")
    import_parser.add_argument("--sheet", required=True, help="Target sheet name")
    import_parser.add_argument("--start-cell", default="A1", help="Start cell, default A1")
    import_parser.add_argument("--header-rows", type=int, default=1, help="Header rows count, default 1")
    import_parser.set_defaults(func=cmd_import_file)

    config_parser = subparsers.add_parser("show-config", help="Print current helper config")
    config_parser.set_defaults(func=cmd_show_config)

    log_parser = subparsers.add_parser("log-path", help="Print today's log file path")
    log_parser.set_defaults(func=cmd_log_path)

    path_parser = subparsers.add_parser("set-tableau-path", help="Save Tableau Desktop executable path")
    path_parser.add_argument("path", help="Path to Tableau Desktop executable")
    path_parser.set_defaults(func=cmd_set_tableau_path)

    mapping_parser = subparsers.add_parser("set-mapping", help="Remember Worksheet to Sheet mapping for a .twb")
    mapping_parser.add_argument("--twb", required=True, help="Path to .twb file")
    mapping_parser.add_argument("--worksheet", required=True, help="Worksheet name")
    mapping_parser.add_argument("--sheet", required=True, help="Target Sheet name")
    mapping_parser.set_defaults(func=cmd_set_mapping)

    status_parser = subparsers.add_parser("automation-status", help="Show Tableau automation implementation status")
    status_parser.set_defaults(func=cmd_automation_status)

    export_parser = subparsers.add_parser("export-tableau", help="Export Tableau worksheets through Tableau Desktop automation")
    export_parser.add_argument("--twb", required=True, help="Path to .twb file")
    export_parser.add_argument("--worksheet", action="append", required=True, help="Worksheet name. Repeat for multiple worksheets.")
    export_parser.add_argument("--export-dir", default="", help="Export directory. Defaults to config.")
    export_parser.add_argument("--format", default="xlsx", choices=["xlsx", "excel"], help="Export format for first draft")
    export_parser.add_argument("--timeout-seconds", type=int, default=0, help="Override timeout seconds")
    export_parser.add_argument("--no-refresh", action="store_true", help="Skip refresh and export cached/current data")
    export_parser.add_argument(
        "--use-cache-on-refresh-failure",
        action="store_true",
        help="Continue export if refresh fails. UI confirmation should be added by the WPS layer.",
    )
    export_parser.set_defaults(func=cmd_export_tableau)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
