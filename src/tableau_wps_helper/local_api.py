from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .job_runner import ImportPlanError, import_plan_result_to_dict, run_import_plan
from .twb_parser import TwbParseError, list_worksheets


class LocalApiError(RuntimeError):
    pass


def serve_local_api(host: str = "127.0.0.1", port: int = 8765) -> None:
    server = ThreadingHTTPServer((host, port), _Handler)
    server.serve_forever()


class _Handler(BaseHTTPRequestHandler):
    server_version = "TableauWpsHelper/0.1"

    def do_OPTIONS(self) -> None:
        self._send_json({"ok": True})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/health":
                self._send_json({"ok": True, "service": "tableau-wps-helper"})
                return
            if parsed.path == "/worksheets":
                params = parse_qs(parsed.query)
                twb = _first(params, "twb")
                if not twb:
                    raise LocalApiError("Missing query parameter: twb")
                worksheets = [item.name for item in list_worksheets(twb)]
                self._send_json({"ok": True, "worksheets": worksheets})
                return
            self._send_json({"ok": False, "error": "Not found"}, status=404)
        except (LocalApiError, TwbParseError) as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            payload = self._read_json()
            if parsed.path == "/import-plan":
                plan = str(payload.get("plan", "")).strip()
                if not plan:
                    raise LocalApiError("Missing JSON field: plan")
                result = run_import_plan(plan)
                body = import_plan_result_to_dict(result)
                self._send_json(body, status=200 if result.ok else 400)
                return
            self._send_json({"ok": False, "error": "Not found"}, status=404)
        except (LocalApiError, ImportPlanError) as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=400)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=500)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LocalApiError("Invalid JSON body.") from exc
        if not isinstance(payload, dict):
            raise LocalApiError("JSON body must be an object.")
        return payload

    def _send_json(self, body: dict[str, object], status: int = 200) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)


def _first(params: dict[str, list[str]], key: str) -> str:
    values = params.get(key, [])
    return values[0].strip() if values else ""
