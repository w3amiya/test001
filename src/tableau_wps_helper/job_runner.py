from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .excel_writer import ImportResult, import_file_to_workbook


@dataclass(frozen=True)
class ImportJob:
    source: str
    workbook: str
    sheet: str
    start_cell: str = "A1"
    header_rows: int = 1


@dataclass(frozen=True)
class ImportPlanResult:
    succeeded: list[ImportResult]
    failed: list[dict[str, str]]

    @property
    def ok(self) -> bool:
        return not self.failed


class ImportPlanError(RuntimeError):
    pass


def load_import_plan(plan_path: str | Path) -> list[ImportJob]:
    path = Path(plan_path).expanduser()
    if not path.exists():
        raise ImportPlanError(f"Import plan not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ImportPlanError(f"Invalid import plan JSON: {path}") from exc

    if not isinstance(raw, dict):
        raise ImportPlanError("Import plan root must be a JSON object.")

    target_workbook = str(raw.get("targetWorkbook", "")).strip()
    default_start_cell = str(raw.get("startCell", "A1")).strip() or "A1"
    default_header_rows = int(raw.get("headerRows", 1))
    items = raw.get("items", [])
    if not isinstance(items, list) or not items:
        raise ImportPlanError("Import plan must contain at least one item.")

    base_dir = path.parent
    jobs: list[ImportJob] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ImportPlanError(f"Import plan item {index} must be a JSON object.")
        source = _resolve_plan_path(base_dir, str(item.get("source", "")).strip())
        workbook = _resolve_plan_path(base_dir, str(item.get("workbook", target_workbook)).strip())
        sheet = str(item.get("sheet", "")).strip()
        start_cell = str(item.get("startCell", default_start_cell)).strip() or default_start_cell
        header_rows = int(item.get("headerRows", default_header_rows))

        if not source:
            raise ImportPlanError(f"Import plan item {index} is missing source.")
        if not workbook:
            raise ImportPlanError(f"Import plan item {index} is missing workbook or targetWorkbook.")
        if not sheet:
            raise ImportPlanError(f"Import plan item {index} is missing sheet.")

        jobs.append(
            ImportJob(
                source=source,
                workbook=workbook,
                sheet=sheet,
                start_cell=start_cell,
                header_rows=header_rows,
            )
        )

    return jobs


def run_import_jobs(jobs: list[ImportJob]) -> ImportPlanResult:
    succeeded: list[ImportResult] = []
    failed: list[dict[str, str]] = []

    for job in jobs:
        try:
            succeeded.append(
                import_file_to_workbook(
                    source_path=job.source,
                    workbook_path=job.workbook,
                    sheet_name=job.sheet,
                    start_cell=job.start_cell,
                    header_rows=job.header_rows,
                )
            )
        except Exception as exc:
            failed.append(
                {
                    "source": job.source,
                    "workbook": job.workbook,
                    "sheet": job.sheet,
                    "error": str(exc),
                }
            )

    return ImportPlanResult(succeeded=succeeded, failed=failed)


def run_import_plan(plan_path: str | Path) -> ImportPlanResult:
    return run_import_jobs(load_import_plan(plan_path))


def import_plan_result_to_dict(result: ImportPlanResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "succeeded": [item.__dict__ for item in result.succeeded],
        "failed": result.failed,
    }


def _resolve_plan_path(base_dir: Path, value: str) -> str:
    if not value:
        return ""
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return str(path)
