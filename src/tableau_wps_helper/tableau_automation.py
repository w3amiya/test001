from __future__ import annotations

import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExportRequest:
    twb_path: str
    worksheets: list[str]
    export_dir: str
    export_format: str = "csv"
    refresh: bool = True
    timeout_seconds: int = 300
    use_cache_on_refresh_failure: bool = True


@dataclass(frozen=True)
class ExportedWorksheet:
    worksheet: str
    file_path: str
    rows: int | None = None


class TableauAutomationUnavailable(RuntimeError):
    pass


class TableauAutomationError(RuntimeError):
    pass


class TableauAutomation:
    """Windows Tableau Desktop automation.

    This is a first-pass UI automation implementation intended for debugging on
    Windows + Tableau Desktop 2025.2. Tableau Desktop does not expose a stable
    local export API for arbitrary worksheet view data, so this module uses
    pywinauto to drive the desktop UI.
    """

    def __init__(self, tableau_desktop_path: str = "") -> None:
        self.tableau_desktop_path = tableau_desktop_path

    def is_available(self) -> bool:
        return bool(self.tableau_desktop_path and Path(self.tableau_desktop_path).expanduser().exists())

    def export_worksheets(self, request: ExportRequest) -> list[ExportedWorksheet]:
        if os.name != "nt":
            raise TableauAutomationUnavailable("Tableau Desktop automation currently requires Windows.")
        if not self.is_available():
            raise TableauAutomationUnavailable(
                "Tableau Desktop path is not configured or does not exist. "
                "Run set-tableau-path first."
            )
        if request.export_format.lower() not in {"xlsx", "excel"}:
            raise TableauAutomationUnavailable(
                "The first automation draft exports Tableau crosstab data as Excel only. "
                "CSV can be generated later by converting the exported Excel file."
            )

        try:
            from pywinauto import Application, Desktop, keyboard
            from pywinauto.timings import TimeoutError as PywinautoTimeoutError
        except ImportError as exc:
            raise TableauAutomationUnavailable(
                "pywinauto is required on Windows. Install it with: pip install pywinauto"
            ) from exc

        export_dir = Path(request.export_dir).expanduser()
        export_dir.mkdir(parents=True, exist_ok=True)
        twb_path = Path(request.twb_path).expanduser()
        if not twb_path.exists():
            raise TableauAutomationError(f"TWB file not found: {twb_path}")

        app = Application(backend="uia").start(f'"{self.tableau_desktop_path}" "{twb_path}"')
        desktop = Desktop(backend="uia")
        deadline = time.time() + max(30, request.timeout_seconds)
        main_window = self._wait_for_tableau_window(desktop, deadline)

        if request.refresh:
            try:
                self._refresh_workbook(main_window, keyboard, deadline)
            except Exception as exc:
                if not request.use_cache_on_refresh_failure:
                    raise TableauAutomationError(f"Refresh failed: {exc}") from exc

        exported: list[ExportedWorksheet] = []
        for worksheet in request.worksheets:
            self._activate_worksheet(main_window, worksheet, deadline)
            file_path = self._export_current_worksheet_to_excel(
                main_window=main_window,
                keyboard=keyboard,
                desktop=desktop,
                workbook_name=twb_path.stem,
                worksheet=worksheet,
                export_dir=export_dir,
                deadline=deadline,
            )
            exported.append(ExportedWorksheet(worksheet=worksheet, file_path=str(file_path), rows=None))

        return exported

    def _wait_for_tableau_window(self, desktop: Any, deadline: float) -> Any:
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                windows = desktop.windows(title_re=".*Tableau.*", visible_only=True)
                if windows:
                    window = windows[0]
                    window.wait("ready", timeout=5)
                    window.set_focus()
                    return window
            except Exception as exc:
                last_error = exc
            time.sleep(1)
        raise TableauAutomationError("Timed out waiting for Tableau Desktop window.") from last_error

    def _refresh_workbook(self, main_window: Any, keyboard: Any, deadline: float) -> None:
        main_window.set_focus()
        # Best effort. Tableau versions/locales differ; F5 and Ctrl+R are both
        # common refresh shortcuts in desktop apps. Menu automation can be
        # tightened after observing the user's Windows environment.
        keyboard.send_keys("{F5}")
        time.sleep(1)
        keyboard.send_keys("^r")
        self._dismiss_nonblocking_dialogs(main_window, deadline, max_seconds=8)

    def _activate_worksheet(self, main_window: Any, worksheet: str, deadline: float) -> None:
        main_window.set_focus()
        # First try direct text lookup. If sheet tabs are not exposed by UIA,
        # this will fail and the Windows debugging pass can replace it with
        # coordinate or menu navigation.
        while time.time() < deadline:
            try:
                candidates = main_window.descendants(title=worksheet)
                for candidate in candidates:
                    if candidate.is_visible():
                        candidate.click_input()
                        time.sleep(1)
                        return
            except Exception:
                pass
            time.sleep(1)
            break
        raise TableauAutomationError(
            f'Unable to activate worksheet "{worksheet}". '
            "The worksheet tab may not be exposed to UI Automation."
        )

    def _export_current_worksheet_to_excel(
        self,
        main_window: Any,
        keyboard: Any,
        desktop: Any,
        workbook_name: str,
        worksheet: str,
        export_dir: Path,
        deadline: float,
    ) -> Path:
        main_window.set_focus()
        target = export_dir / f"{_safe_name(workbook_name)}_{_safe_name(worksheet)}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"

        # Try menu path first. This is expected to work in English Tableau. For
        # Chinese UI, the hotkey fallback below may need adjustment on Windows.
        menu_attempted = False
        try:
            main_window.menu_select("Worksheet->Export->Crosstab to Excel")
            menu_attempted = True
        except Exception:
            pass

        if not menu_attempted:
            # Best-effort fallback: Alt opens menu. The exact accelerators differ
            # by locale, so this is intentionally conservative and may need
            # tuning after first Windows run.
            keyboard.send_keys("%w")
            time.sleep(0.5)
            keyboard.send_keys("e")
            time.sleep(0.5)
            keyboard.send_keys("c")

        self._handle_save_dialog(desktop, target, deadline)
        self._wait_for_file(target, deadline)
        return target

    def _handle_save_dialog(self, desktop: Any, target: Path, deadline: float) -> None:
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                dialogs = desktop.windows(title_re=".*(Save|保存|另存为).*", visible_only=True)
                if dialogs:
                    dialog = dialogs[0]
                    dialog.set_focus()
                    edits = dialog.descendants(control_type="Edit")
                    if edits:
                        edits[0].set_edit_text(str(target))
                    buttons = dialog.descendants(control_type="Button")
                    for button in buttons:
                        title = button.window_text()
                        if title in {"Save", "保存", "确定", "&Save"}:
                            button.click_input()
                            return
                    # Fallback to Enter if the Save button text is not exposed.
                    dialog.type_keys("{ENTER}")
                    return
            except Exception as exc:
                last_error = exc
            time.sleep(1)
        raise TableauAutomationError("Timed out waiting for Tableau save dialog.") from last_error

    def _wait_for_file(self, target: Path, deadline: float) -> None:
        while time.time() < deadline:
            if target.exists() and target.stat().st_size > 0:
                return
            time.sleep(1)
        raise TableauAutomationError(f"Timed out waiting for export file: {target}")

    def _dismiss_nonblocking_dialogs(self, main_window: Any, deadline: float, max_seconds: int = 8) -> None:
        end = min(deadline, time.time() + max_seconds)
        while time.time() < end:
            try:
                for button_text in ("OK", "确定", "Close", "关闭"):
                    buttons = main_window.descendants(title=button_text, control_type="Button")
                    for button in buttons:
                        if button.is_visible():
                            button.click_input()
                            return
            except Exception:
                pass
            time.sleep(1)


def build_export_path(export_dir: str | Path, workbook_name: str, worksheet: str, suffix: str) -> Path:
    safe_workbook = _safe_name(workbook_name)
    safe_worksheet = _safe_name(worksheet)
    return Path(export_dir).expanduser() / f"{safe_workbook}_{safe_worksheet}.{suffix.lstrip('.')}"


def _safe_name(value: str) -> str:
    invalid = '<>:"/\\\\|?*'
    cleaned = "".join("_" if ch in invalid else ch for ch in value.strip())
    return cleaned or "export"
