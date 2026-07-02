from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default_config.json"
USER_CONFIG_PATH = Path.home() / ".tableau_wps_helper" / "config.json"
FALLBACK_CONFIG_PATH = Path(tempfile.gettempdir()) / "tableau_wps_helper_config.json"


@dataclass
class HelperConfig:
    tableau_desktop_path: str = ""
    default_export_dir: str = "~/Documents/DataExportPlugin/Tableau"
    default_log_dir: str = "~/Documents/TableauExports/logs"
    recent_twb_files_limit: int = 5
    recent_twb_files: list[str] = field(default_factory=list)
    default_timeout_seconds: int = 300
    default_start_cell: str = "A1"
    default_header_rows: int = 1
    worksheet_sheet_mappings: dict[str, dict[str, str]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "HelperConfig":
        return cls(
            tableau_desktop_path=raw.get("tableauDesktopPath", ""),
            default_export_dir=raw.get("defaultExportDir", "~/Documents/DataExportPlugin/Tableau"),
            default_log_dir=raw.get("defaultLogDir", "~/Documents/TableauExports/logs"),
            recent_twb_files_limit=int(raw.get("recentTwbFilesLimit", 5)),
            recent_twb_files=list(raw.get("recentTwbFiles", [])),
            default_timeout_seconds=int(raw.get("defaultTimeoutSeconds", 300)),
            default_start_cell=raw.get("defaultStartCell", "A1"),
            default_header_rows=int(raw.get("defaultHeaderRows", 1)),
            worksheet_sheet_mappings=dict(raw.get("worksheetSheetMappings", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tableauDesktopPath": self.tableau_desktop_path,
            "defaultExportDir": self.default_export_dir,
            "defaultLogDir": self.default_log_dir,
            "recentTwbFilesLimit": self.recent_twb_files_limit,
            "recentTwbFiles": self.recent_twb_files[: self.recent_twb_files_limit],
            "defaultTimeoutSeconds": self.default_timeout_seconds,
            "defaultStartCell": self.default_start_cell,
            "defaultHeaderRows": self.default_header_rows,
            "worksheetSheetMappings": self.worksheet_sheet_mappings,
        }

    def add_recent_twb(self, path: str) -> None:
        normalized = str(Path(path).expanduser())
        self.recent_twb_files = [p for p in self.recent_twb_files if p != normalized]
        self.recent_twb_files.insert(0, normalized)
        self.recent_twb_files = self.recent_twb_files[: self.recent_twb_files_limit]

    def set_sheet_mapping(self, twb_path: str, worksheet: str, sheet: str) -> None:
        key = str(Path(twb_path).expanduser())
        self.worksheet_sheet_mappings.setdefault(key, {})[worksheet] = sheet


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def user_config_path() -> Path:
    override = os.environ.get("TABLEAU_WPS_HELPER_CONFIG", "").strip()
    if override:
        return Path(override).expanduser()
    return USER_CONFIG_PATH


def load_config(path: Path | None = None) -> HelperConfig:
    if path is None:
        path = user_config_path()
    base = _read_json(DEFAULT_CONFIG_PATH)
    override = _read_json(path)
    merged = {**base, **override}
    return HelperConfig.from_dict(merged)


def save_config(config: HelperConfig, path: Path | None = None) -> None:
    if path is None:
        path = user_config_path()
    content = json.dumps(config.to_dict(), ensure_ascii=False, indent=2)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError:
        if path != USER_CONFIG_PATH:
            raise
        FALLBACK_CONFIG_PATH.write_text(content, encoding="utf-8")


def expand_path(path: str) -> Path:
    return Path(path).expanduser().resolve()
