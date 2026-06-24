#!/usr/bin/env python3
"""Self-contained MCP stdio client that exercises the Google Sheets MCP App server.

arcade-mcp's stdio transport is newline-delimited JSON (one JSON-RPC message per line),
so this speaks the protocol directly — no SDK required. It runs the full MCP App flow:

  initialize -> notifications/initialized -> tools/list -> tools/call (x2)
  -> resources/list -> resources/templates/list -> resources/read (x3)

and asserts the MCP Apps wiring:
  * each tool carries _meta.ui.resourceUri
  * the ui:// bridge resources serve text/html;profile=mcp-app
  * tools/call returns structuredContent (grid values / embed url) + the preview_uri
  * resources/read of the templated preview_uri returns renderable HTML (<table>/<iframe>)

Fetched HTML is written next to this file (grid_preview.html, embed_preview.html,
grid_bridge.html) so the grid can be opened/screenshotted without an Apps host.

Run:  uv run python mcp_smoke_client.py        (from the arcade-mcp repo root or this dir)
Exit code 0 = all checks passed.
"""

import json
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = str(HERE / "server.py")
PROTOCOL_VERSION = "2025-06-18"

_checks: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> bool:
    _checks.append((bool(ok), label))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    return bool(ok)


class StdioMCP:
    def __init__(self, server_path: str):
        self.proc = subprocess.Popen(
            [sys.executable, server_path, "stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        self._q: queue.Queue[dict] = queue.Queue()
        self._stderr: list[str] = []
        self._next_id = 1
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._read_stderr, daemon=True).start()

    def _read_stdout(self) -> None:
        assert self.proc.stdout
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._q.put(json.loads(line))
            except json.JSONDecodeError:
                self._stderr.append(f"[stdout-nonjson] {line}")

    def _read_stderr(self) -> None:
        assert self.proc.stderr
        for line in self.proc.stderr:
            self._stderr.append(line.rstrip())

    def _send(self, obj: dict) -> None:
        assert self.proc.stdin
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def request(self, method: str, params: dict | None = None, timeout: float = 20.0) -> dict:
        rid = self._next_id
        self._next_id += 1
        self._send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        while True:
            try:
                msg = self._q.get(timeout=timeout)
            except queue.Empty:
                raise TimeoutError(f"No response to {method!r}. stderr tail:\n" + "\n".join(self._stderr[-15:]))
            if msg.get("id") == rid:
                if "error" in msg:
                    raise RuntimeError(f"{method} error: {msg['error']}")
                return msg.get("result", {})

    def notify(self, method: str, params: dict | None = None) -> None:
        self._send({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def main() -> int:
    cli = StdioMCP(SERVER)
    try:
        print("== initialize ==")
        init = cli.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "smoke-client", "version": "0.0.1"},
            },
        )
        cli.notify("notifications/initialized", {})
        si = init.get("serverInfo", {})
        check(si.get("name") == "google_sheets_app", f"serverInfo.name == google_sheets_app (got {si.get('name')!r})")
        check("resources" in init.get("capabilities", {}), "server advertises resources capability")

        print("== tools/list ==")
        tools = cli.request("tools/list").get("tools", [])
        by_name = {t["name"]: t for t in tools}
        print("  tools:", list(by_name))
        grid_tool = by_name.get("GoogleSheetsApp_RenderRangePreview", {})
        embed_tool = by_name.get("GoogleSheetsApp_RenderSheetEmbed", {})
        check(bool(grid_tool), "tool GoogleSheetsApp_RenderRangePreview present")
        check(bool(embed_tool), "tool GoogleSheetsApp_RenderSheetEmbed present")
        grid_ui = (grid_tool.get("_meta") or {}).get("ui", {}).get("resourceUri")
        embed_ui = (embed_tool.get("_meta") or {}).get("ui", {}).get("resourceUri")
        check(grid_ui == "ui://google_sheets_app/grid.html", f"grid tool _meta.ui.resourceUri (got {grid_ui!r})")
        check(embed_ui == "ui://google_sheets_app/embed.html", f"embed tool _meta.ui.resourceUri (got {embed_ui!r})")

        print("== resources/list + templates/list ==")
        res = cli.request("resources/list").get("resources", [])
        tmpls = cli.request("resources/templates/list").get("resourceTemplates", [])
        res_uris = {r["uri"]: r for r in res}
        tmpl_uris = {t["uriTemplate"]: t for t in tmpls}
        print("  resources:", list(res_uris))
        print("  templates:", list(tmpl_uris))
        gb = res_uris.get("ui://google_sheets_app/grid.html", {})
        check(gb.get("mimeType") == "text/html;profile=mcp-app", "grid.html served as text/html;profile=mcp-app")
        check("ui://google_sheets_app/embed.html" in res_uris, "embed.html bridge resource present")
        _eb_csp = (((res_uris.get("ui://google_sheets_app/embed.html", {}).get("_meta") or {}).get("ui") or {}).get("csp") or {})
        check("https://docs.google.com" in (_eb_csp.get("frameDomains") or []),
              "embed UI declares _meta.ui.csp.frameDomains for docs.google.com")
        check("ui://google_sheets_app/grid/{spreadsheet_id}/{a1_range}" in tmpl_uris, "grid template resource present")
        check("ui://google_sheets_app/embed/{spreadsheet_id}/{gid}" in tmpl_uris, "embed template resource present")

        print("== tools/call GoogleSheetsApp_RenderRangePreview ==")
        r1 = cli.request("tools/call", {"name": "GoogleSheetsApp_RenderRangePreview",
                                        "arguments": {"spreadsheet_id": "DEMO_SHEET_ID", "a1_range": "Sheet1!A1:D6"}})
        sc1 = r1.get("structuredContent") or {}
        check(r1.get("isError") is False, "grid tool isError == False")
        check(isinstance(sc1.get("values"), list) and len(sc1["values"]) == 6, f"grid returned 6 rows (got {len(sc1.get('values', []))})")
        check(sc1.get("columns") == ["A", "B", "C", "D"], f"grid columns A..D (got {sc1.get('columns')})")
        check("ui_resource_uri" not in sc1, "grid output drops non-standard ui_resource_uri (SEP-1865 linkage is tools/list _meta.ui.resourceUri)")
        grid_preview_uri = sc1.get("preview_uri", "")
        check(grid_preview_uri.startswith("ui://google_sheets_app/grid/"), f"grid preview_uri is a ui:// resource (got {grid_preview_uri!r})")
        check(any(c.get("type") == "text" for c in r1.get("content", [])), "grid tool also returns text content")
        # gap 1: review flags + where-to-look-first
        flags1 = sc1.get("flags")
        check(isinstance(flags1, list) and len(flags1) >= 1, f"grid returns gap-1 review flags (got {len(flags1 or [])})")
        check(all({"cell", "severity", "reason"} <= set(f) for f in (flags1 or [])), "each flag has cell/severity/reason")
        check(isinstance(sc1.get("where_to_look_first"), list) and bool(sc1.get("where_to_look_first")),
              "grid returns a 'where_to_look_first' list (gap 1)")
        check(any(f.get("severity") == "high" for f in (flags1 or [])), "grid flags at least one high-severity cell")

        print("== tools/call GoogleSheetsApp_RenderSheetEmbed ==")
        r2 = cli.request("tools/call", {"name": "GoogleSheetsApp_RenderSheetEmbed",
                                        "arguments": {"spreadsheet_id": "DEMO_SHEET_ID", "gid": "12345"}})
        sc2 = r2.get("structuredContent") or {}
        check(r2.get("isError") is False, "embed tool isError == False")
        eurl = sc2.get("embed_url", "")
        check("/preview" in eurl and "DEMO_SHEET_ID" in eurl, f"embed_url uses /preview (got {eurl!r})")
        check("/edit" not in eurl, "embed_url avoids the X-Frame-blocked /edit URL")
        embed_preview_uri = sc2.get("preview_uri", "")
        check(embed_preview_uri.startswith("ui://google_sheets_app/embed/"), f"embed preview_uri is a ui:// resource (got {embed_preview_uri!r})")
        flags2 = sc2.get("flags")
        check(isinstance(flags2, list) and len(flags2) >= 1, f"embed returns gap-1 review flags (got {len(flags2 or [])})")
        check(isinstance(sc2.get("where_to_look_first"), list) and bool(sc2.get("where_to_look_first")),
              "embed returns a 'where_to_look_first' list (gap 1)")

        print("== resources/read (bridge + baked previews) ==")
        bridge = cli.request("resources/read", {"uri": "ui://google_sheets_app/grid.html"})
        bridge_html = (bridge.get("contents") or [{}])[0].get("text", "")
        check("ui/initialize" in bridge_html, "grid bridge HTML performs ui/initialize handshake")
        check("ui/notifications/tool-result" in bridge_html, "grid bridge consumes the standard ui/notifications/tool-result delivery")
        check("protocolVersion" in bridge_html, "grid bridge sends protocolVersion in ui/initialize (hosts require it)")
        (HERE / "grid_bridge.html").write_text(bridge_html, encoding="utf-8")

        gprev = cli.request("resources/read", {"uri": grid_preview_uri})
        gprev_html = (gprev.get("contents") or [{}])[0].get("text", "")
        check("<table>" in gprev_html and "DEMO_SHEET_ID" in gprev_html, "baked grid preview is a renderable <table> for the sheet")
        check("Where to look first" in gprev_html, "baked grid preview includes the gap-1 review panel")
        check(("flag-high" in gprev_html) or ("flag-medium" in gprev_html), "baked grid preview highlights a flagged cell")
        (HERE / "grid_preview.html").write_text(gprev_html, encoding="utf-8")

        eprev = cli.request("resources/read", {"uri": embed_preview_uri})
        eprev_html = (eprev.get("contents") or [{}])[0].get("text", "")
        check("<iframe" in eprev_html and "/preview" in eprev_html, "baked embed preview frames the live sheet via /preview")
        check("Where to look first" in eprev_html, "baked embed preview includes the gap-1 review panel")
        (HERE / "embed_preview.html").write_text(eprev_html, encoding="utf-8")

        print(f"\nWrote: grid_bridge.html, grid_preview.html, embed_preview.html to {HERE}")
    finally:
        cli.close()

    passed = sum(1 for ok, _ in _checks if ok)
    total = len(_checks)
    print(f"\n==== {passed}/{total} checks passed ====")
    if passed != total:
        print("FAILURES:")
        for ok, label in _checks:
            if not ok:
                print("  -", label)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
