#!/usr/bin/env python3
"""Google Sheets MCP App — a proof-of-concept MCP Apps server.

Demonstrates the MCP Apps pattern (SEP-1865, https://modelcontextprotocol.io/extensions/apps)
on top of ``arcade-mcp-server``:

  * Two tools, each linked to an HTML UI via ``meta={"ui": {"resourceUri": "ui://..."}}``.
  * The UI is a normal MCP *resource* served as ``text/html;profile=mcp-app``.
  * A real MCP Apps host (Claude web/desktop, the ext-apps basic-host) fetches the
    UI resource, renders it in a sandboxed iframe, and pushes the tool result into it.

Two tools:

  1. ``render_range_preview(spreadsheet_id, a1_range)``  — renders a sample spreadsheet
     grid (an HTML <table>) for the given A1 range.
  2. ``render_sheet_embed(spreadsheet_id, gid)``         — renders the live sheet inside
     an <iframe> using the embeddable /preview URL.

Gap 1 (the point of the spike, TOO-1337): the reviewer's problem isn't "show me the
sheet", it's "where do I look first?". Doc->spreadsheet extraction is lossy, so both
tools also surface **review flags** — the cells the agent was unsure about, with a
reason and a deep-link into the live sheet. That is the signal that turns a wall of
cells into "check D2 and B3 first", solving gap 1 instead of just rendering.

Two flavors of UI resource are registered for each tool:

  * A *fixed bridge* resource (``ui://google_sheets_app/grid.html`` / ``.../embed.html``)
    — the spec-correct MCP App UI that ``meta.ui.resourceUri`` points at. It performs the
    ``ui/initialize`` handshake and renders whatever tool result the host pushes in.
  * A *static templated* resource (``ui://google_sheets_app/grid/{spreadsheet_id}/{a1_range}``
    and ``ui://google_sheets_app/embed/{spreadsheet_id}/{gid}``) — a fully self-contained
    HTML document with the data baked in. This needs no Apps host, so a plain MCP client can
    ``resources/read`` it and get renderable HTML. Each tool returns this concrete URI in its
    structured output as ``preview_uri`` for host-independent rendering / verification.

This is a POC: the grid uses generated *sample* data (no Google OAuth) with a few
deliberately-injected extraction problems so the gap-1 flags have something to point at,
and the embed uses a public sample spreadsheet so the iframe actually loads.
"""

import re
import sys
from typing import Annotated, TypedDict
from urllib.parse import quote, unquote

from arcade_mcp_server import MCPApp

app = MCPApp(
    name="google_sheets_app",
    version="0.2.0",
    instructions="POC MCP Apps server that renders Google Sheets ranges as an interactive grid or a live iframe, with review flags that point the user at the cells the agent was unsure about.",
    log_level="INFO",
)

# ---------------------------------------------------------------------------
# Constraints (keep the UI useful and the payloads small)
# ---------------------------------------------------------------------------
MAX_COLS = 26  # A..Z — one letter, keeps the grid legible
MAX_ROWS = 50  # cap rows so the HTML payload stays small in the MCP message

# A public, viewable sample spreadsheet (Google's documented "Class Data" sheet),
# used as the default so the embed iframe actually renders in a demo.
DEFAULT_SAMPLE_SPREADSHEET_ID = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"

GRID_BRIDGE_URI = "ui://google_sheets_app/grid.html"
EMBED_BRIDGE_URI = "ui://google_sheets_app/embed.html"


# ---------------------------------------------------------------------------
# A1 notation + sample data
# ---------------------------------------------------------------------------
_A1_CELL = re.compile(r"^([A-Za-z]+)?(\d+)?$")


def _col_to_index(letters: str) -> int:
    """'A' -> 0, 'B' -> 1, 'Z' -> 25, 'AA' -> 26."""
    idx = 0
    for ch in letters.upper():
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def _index_to_col(idx: int) -> str:
    """0 -> 'A', 25 -> 'Z', 26 -> 'AA'."""
    letters = ""
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        letters = chr(ord("A") + rem) + letters
    return letters


class _ParsedRange(TypedDict):
    sheet_name: str
    start_col: int
    start_row: int
    width: int
    height: int
    truncated: bool


def parse_a1_range(a1_range: str) -> _ParsedRange:
    """Parse an A1 range like ``Sheet1!A1:C10`` / ``A1:E20`` / ``B2`` into bounds.

    Whole-column refs (``A:C``) and missing rows default to a sample height.
    Width/height are capped at :data:`MAX_COLS` / :data:`MAX_ROWS`.
    """
    raw = (a1_range or "").strip() or "A1:E10"
    sheet_name = ""
    if "!" in raw:
        sheet_name, raw = raw.split("!", 1)
        sheet_name = sheet_name.strip().strip("'")

    parts = raw.split(":")
    start_ref = parts[0].strip()
    end_ref = parts[1].strip() if len(parts) > 1 else start_ref

    def _cell(ref: str) -> tuple[str | None, str | None]:
        mm = _A1_CELL.match(ref)
        return (mm.group(1), mm.group(2)) if mm else (None, None)

    s_col_l, s_row = _cell(start_ref)
    e_col_l, e_row = _cell(end_ref)

    start_col = _col_to_index(s_col_l) if s_col_l else 0
    end_col = _col_to_index(e_col_l) if e_col_l else start_col + 4
    start_row = int(s_row) if s_row else 1
    end_row = int(e_row) if e_row else start_row + 9

    if end_col < start_col:
        start_col, end_col = end_col, start_col
    if end_row < start_row:
        start_row, end_row = end_row, start_row

    full_width = end_col - start_col + 1
    full_height = end_row - start_row + 1
    width = max(1, min(full_width, MAX_COLS))
    height = max(1, min(full_height, MAX_ROWS))

    return _ParsedRange(
        sheet_name=sheet_name,
        start_col=start_col,
        start_row=start_row,
        width=width,
        height=height,
        truncated=(width < full_width or height < full_height),
    )


_HEADER_POOL = [
    "Name", "Email", "Department", "Start Date", "Salary",
    "Status", "Manager", "Location", "Employee ID", "Notes",
]
_NAMES = ["Ada Lovelace", "Alan Turing", "Grace Hopper", "Katherine Johnson",
          "Linus Torvalds", "Margaret Hamilton", "Dennis Ritchie", "Barbara Liskov"]
_DEPTS = ["Engineering", "Design", "Sales", "Support", "Finance", "Marketing"]
_LOCS = ["NYC", "SF", "London", "Berlin", "Tokyo", "Remote"]


def _sample_cell(header: str, row_seed: int, col_idx: int) -> str:
    """Deterministic, themed sample value for a data cell."""
    h = header.lower()
    if "name" in h and "id" not in h:
        return _NAMES[row_seed % len(_NAMES)]
    if "email" in h:
        first = _NAMES[row_seed % len(_NAMES)].split()[0].lower()
        return f"{first}@example.com"
    if "department" in h:
        return _DEPTS[row_seed % len(_DEPTS)]
    if "date" in h:
        return f"20{20 + (row_seed % 5)}-{1 + (row_seed % 12):02d}-{1 + (row_seed % 28):02d}"
    if "salary" in h:
        return f"${90 + (row_seed * 7 % 80)},000"
    if "status" in h:
        return ["Active", "On leave", "Active", "Contractor"][row_seed % 4]
    if "manager" in h:
        return _NAMES[(row_seed + 3) % len(_NAMES)]
    if "location" in h:
        return _LOCS[row_seed % len(_LOCS)]
    if "id" in h:
        return f"EMP-{1000 + row_seed}"
    return f"r{row_seed + 1}c{col_idx + 1}"


def generate_sample_grid(parsed: _ParsedRange) -> list[list[str]]:
    """Build a 2D grid of sample strings sized to the parsed range.

    The first row is a header row; the remaining rows are themed sample data.
    A few cells are then perturbed (see :func:`_inject_anomalies`) so the gap-1
    review flags have realistic problems to point at.
    """
    width, height = parsed["width"], parsed["height"]
    headers = [
        _HEADER_POOL[c] if c < len(_HEADER_POOL) else f"Field {_index_to_col(parsed['start_col'] + c)}"
        for c in range(width)
    ]
    grid: list[list[str]] = [headers]
    for r in range(1, height):
        grid.append([_sample_cell(headers[c], r - 1, c) for c in range(width)])
    _inject_anomalies(grid)
    return grid


# ---------------------------------------------------------------------------
# Gap 1: review flags — surface what the agent was unsure about / where to look
# ---------------------------------------------------------------------------
class ReviewFlag(TypedDict):
    cell: str  # A1 reference, e.g. "D2"
    severity: str  # "high" | "medium" | "low"
    reason: str  # what the agent was unsure about


_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _col_offset(headers: list[str], needle: str) -> int | None:
    for i, h in enumerate(headers):
        if needle in h.lower():
            return i
    return None


def _inject_anomalies(grid: list[list[str]]) -> None:
    """Deterministically introduce a few realistic doc->spreadsheet extraction
    problems so the gap-1 flags point at something concrete (POC stand-in for
    the confidence signal a real extraction agent would emit)."""
    if len(grid) < 2:
        return
    headers, height = grid[0], len(grid)
    c = _col_offset(headers, "email")  # blank cell the agent couldn't extract
    if c is not None and height > 2:
        grid[2][c] = ""
    c = _col_offset(headers, "salary")  # OCR artifact: letter inside a number
    if c is not None and height > 1:
        grid[1][c] = "$9O,000"  # capital O instead of zero
    c = _col_offset(headers, "date")  # invalid/ambiguous date
    if c is not None and height > 1:
        grid[1][c] = "2021-13-05"  # month 13


def _valid_iso_date(text: str) -> bool:
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return False
    _y, m, d = (int(x) for x in text.split("-"))
    return 1 <= m <= 12 and 1 <= d <= 31


def detect_review_flags(parsed: _ParsedRange, grid: list[list[str]]) -> list[ReviewFlag]:
    """Scan the grid for the cells a reviewer should check first (gap 1)."""
    flags: list[ReviewFlag] = []
    if not grid:
        return flags
    headers = grid[0]
    start_col, start_row = parsed["start_col"], parsed["start_row"]
    for r in range(1, len(grid)):
        for c, val in enumerate(grid[r]):
            a1 = f"{_index_to_col(start_col + c)}{start_row + r}"
            text = str(val).strip()
            header = headers[c] if c < len(headers) else ""
            hl = header.lower()
            if text == "":
                flags.append(ReviewFlag(
                    cell=a1, severity="high",
                    reason=f"'{header}' was blank in the source — the agent could not extract a value.",
                ))
            elif "salary" in hl and re.search(r"[A-Za-z]", text):
                flags.append(ReviewFlag(
                    cell=a1, severity="high",
                    reason=f"Couldn't confidently parse '{text}' — likely an OCR artifact (a letter inside a number).",
                ))
            elif "date" in hl and not _valid_iso_date(text):
                flags.append(ReviewFlag(
                    cell=a1, severity="medium",
                    reason=f"Date '{text}' is invalid/ambiguous in the source — verify.",
                ))
    if len(headers) > 1:  # a low-confidence, always-present "inferred header" flag
        a1 = f"{_index_to_col(start_col + len(headers) - 1)}{start_row}"
        flags.append(ReviewFlag(
            cell=a1, severity="low",
            reason=f"Header '{headers[-1]}' was inferred from a merged/spanning cell — confirm the label.",
        ))
    flags.sort(key=lambda f: _SEVERITY_RANK.get(f["severity"], 9))
    return flags


def where_to_look_first(flags: list[ReviewFlag]) -> list[str]:
    """Flat, ordered "go check these" list for the model/chat (gap 1)."""
    return [f"{f['cell']} — {f['reason']}" for f in flags]


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------
def edit_url(spreadsheet_id: str, gid: str = "", cell: str = "") -> str:
    base = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
    frag = []
    if gid:
        frag.append(f"gid={gid}")
    if cell:
        frag.append(f"range={cell}")
    return f"{base}#{'&'.join(frag)}" if frag else base


def embed_url(spreadsheet_id: str, gid: str = "") -> str:
    """Embeddable, read-only preview URL.

    The ``/edit`` URL is X-Frame-Options-blocked; ``/preview`` is the framable
    read-only view (for sheets the viewer's browser session can access).
    """
    base = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/preview"
    return f"{base}?gid={gid}&widget=true&headers=false" if gid else f"{base}?widget=true&headers=false"


def _grid_preview_uri(spreadsheet_id: str, a1_range: str) -> str:
    # Keep '!' and ':' literal so they stay inside one URI-template path segment.
    return f"ui://google_sheets_app/grid/{quote(spreadsheet_id, safe='')}/{quote(a1_range, safe='!:')}"


def _embed_preview_uri(spreadsheet_id: str, gid: str) -> str:
    return f"ui://google_sheets_app/embed/{quote(spreadsheet_id, safe='')}/{quote(gid or 'default', safe='')}"


# ---------------------------------------------------------------------------
# HTML builders (self-contained, inline CSS/JS — host iframe is deny-by-default CSP)
# ---------------------------------------------------------------------------
def _esc(s: str) -> str:
    return (
        str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


_GRID_CSS = """
  * { box-sizing: border-box; }
  body { font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 12px;
         background: #f8fafc; color: #1e293b; }
  .meta { font-size: 12px; color: #64748b; margin-bottom: 8px; }
  .meta b { color: #334155; }
  .wrap { overflow: auto; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; }
  table { border-collapse: collapse; font-size: 13px; width: 100%; }
  th, td { border: 1px solid #e2e8f0; padding: 4px 8px; text-align: left; white-space: nowrap; }
  thead th, .rowhdr { background: #f1f5f9; color: #475569; font-weight: 600;
                      position: sticky; top: 0; text-align: center; }
  .rowhdr { position: static; width: 42px; }
  tbody tr:first-child td { background: #eef2ff; font-weight: 600; }
  .badge { display: inline-block; background: #fef3c7; color: #92400e; border-radius: 4px;
           padding: 1px 6px; font-size: 11px; margin-left: 6px; }
  /* gap-1: flagged cells */
  td.flag-high { background: #fee2e2; outline: 2px solid #ef4444; outline-offset: -2px; }
  td.flag-medium { background: #fef3c7; outline: 2px solid #f59e0b; outline-offset: -2px; }
  td.flag-low { background: #e0e7ff; outline: 2px solid #6366f1; outline-offset: -2px; }
  td .flagdot { float: right; margin-left: 6px; font-size: 11px; }
  /* gap-1: "where to look first" panel */
  .review { border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; padding: 10px 12px;
            margin-bottom: 10px; }
  .review h2 { font-size: 13px; margin: 0 0 8px; color: #0f172a; }
  .review ul { margin: 0; padding: 0; list-style: none; }
  .review li { display: flex; gap: 8px; align-items: baseline; padding: 4px 0;
               border-top: 1px solid #f1f5f9; }
  .review li:first-child { border-top: 0; }
  .pill { flex: none; font-size: 11px; font-weight: 700; border-radius: 4px; padding: 1px 6px; }
  .pill.high { background: #fee2e2; color: #b91c1c; }
  .pill.medium { background: #fef3c7; color: #92400e; }
  .pill.low { background: #e0e7ff; color: #3730a3; }
  .review a.cell { flex: none; font-weight: 600; color: #2563eb; text-decoration: none;
                   font-variant-numeric: tabular-nums; }
  .review .why { color: #475569; }
  .review .clean { color: #166534; font-size: 13px; }
"""


def _flag_panel_html(flags: list[ReviewFlag], spreadsheet_id: str, gid: str = "") -> str:
    """The gap-1 "where to look first" panel, with deep-links into the live sheet."""
    if not flags:
        return (
            '<div class="review"><h2>Review</h2>'
            '<div class="clean">✓ No low-confidence cells — nothing flagged for review.</div></div>'
        )
    items = []
    for f in flags:
        link = edit_url(spreadsheet_id, gid, f["cell"])
        items.append(
            f'<li><span class="pill {_esc(f["severity"])}">{_esc(f["severity"])}</span>'
            f'<a class="cell" href="{_esc(link)}" target="_blank" rel="noopener">{_esc(f["cell"])}</a>'
            f'<span class="why">{_esc(f["reason"])}</span></li>'
        )
    return (
        f'<div class="review"><h2>Where to look first ({len(flags)})</h2>'
        f'<ul>{"".join(items)}</ul></div>'
    )


def render_grid_table(parsed: _ParsedRange, values: list[list[str]], flags: list[ReviewFlag]) -> str:
    """Spreadsheet-like <table>: column-letter header + row-number gutter, with
    flagged cells highlighted (gap 1)."""
    start_col, start_row = parsed["start_col"], parsed["start_row"]
    width = parsed["width"]
    col_letters = [_index_to_col(start_col + c) for c in range(width)]
    by_cell = {f["cell"]: f for f in flags}

    head = "".join(f"<th>{_esc(c)}</th>" for c in col_letters)
    rows_html = []
    for i, row in enumerate(values):
        cells = []
        for c, v in enumerate(row):
            a1 = f"{_index_to_col(start_col + c)}{start_row + i}"
            flag = by_cell.get(a1)
            if flag:
                cls = f' class="flag-{_esc(flag["severity"])}" title="{_esc(flag["reason"])}"'
                dot = '<span class="flagdot">⚠</span>'
            else:
                cls, dot = "", ""
            cells.append(f"<td{cls}>{_esc(str(v))}{dot}</td>")
        rows_html.append(f'<tr><th class="rowhdr">{start_row + i}</th>{"".join(cells)}</tr>')
    body = "".join(rows_html)
    return (
        f'<div class="wrap"><table>'
        f'<thead><tr><th class="rowhdr"></th>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )


def render_grid_document(spreadsheet_id: str, a1_range: str) -> str:
    """Complete standalone HTML grid for the static templated resource."""
    parsed = parse_a1_range(a1_range)
    values = generate_sample_grid(parsed)
    flags = detect_review_flags(parsed, values)
    table = render_grid_table(parsed, values, flags)
    panel = _flag_panel_html(flags, spreadsheet_id)
    sheet = f"{parsed['sheet_name']}!" if parsed["sheet_name"] else ""
    trunc = '<span class="badge">truncated to fit</span>' if parsed["truncated"] else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Sheet preview {_esc(sheet)}{_esc(a1_range)}</title>
<style>{_GRID_CSS}</style></head>
<body>
  <div class="meta">Spreadsheet <b>{_esc(spreadsheet_id)}</b> &middot; range <b>{_esc(sheet)}{_esc(a1_range)}</b>
    &middot; sample data {trunc}</div>
  {panel}
  {table}
</body></html>"""


def render_embed_document(spreadsheet_id: str, gid: str) -> str:
    """Complete standalone HTML that frames the live sheet via the /preview URL,
    alongside the gap-1 review panel (deep-links jump into the live sheet)."""
    g = "" if (not gid or gid == "default") else gid
    url = embed_url(spreadsheet_id, g)
    link = edit_url(spreadsheet_id, g)
    # Reuse the flag logic on a default range so the review panel has content.
    parsed = parse_a1_range("A1:E10")
    flags = detect_review_flags(parsed, generate_sample_grid(parsed))
    panel = _flag_panel_html(flags, spreadsheet_id, g)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Live sheet {_esc(spreadsheet_id)}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: system-ui, sans-serif; margin: 0; padding: 12px; background: #f8fafc; color:#1e293b; }}
  .meta {{ font-size: 12px; color: #64748b; margin-bottom: 8px; }}
  .meta a {{ color: #2563eb; }}
  .cols {{ display: grid; grid-template-columns: 1fr 340px; gap: 12px; align-items: start; }}
  @media (max-width: 760px) {{ .cols {{ grid-template-columns: 1fr; }} }}
  .frame {{ width: 100%; height: 70vh; min-height: 420px; border: 1px solid #cbd5e1;
            border-radius: 6px; background: #fff; }}
  iframe {{ width: 100%; height: 100%; border: 0; border-radius: 6px; }}
{_GRID_CSS}
</style></head>
<body>
  <div class="meta">Live read-only embed of <b>{_esc(spreadsheet_id)}</b>
    &middot; <a href="{_esc(link)}" target="_blank" rel="noopener">open in Google Sheets</a></div>
  <div class="cols">
    <div class="frame">
      <iframe src="{_esc(url)}" sandbox="allow-scripts allow-same-origin allow-popups"
              referrerpolicy="no-referrer-when-downgrade" loading="lazy"
              title="Google Sheet preview"></iframe>
    </div>
    {panel}
  </div>
</body></html>"""


# Minimal JSON-RPC-over-postMessage bridge shared by the two fixed "MCP App" UIs.
# Mirrors examples/mcp_servers/resources/src/resources/app.html and additionally
# renders whatever tool result the host pushes in after render (app.ontoolresult).
_BRIDGE_JS = """
const JSONRPC = "2.0";
let nextId = 1; const pending = {};
const $ = (id) => document.getElementById(id);

function post(msg) { window.parent.postMessage(Object.assign({jsonrpc: JSONRPC}, msg), "*"); }
function rpc(method, params) {
  return new Promise((resolve, reject) => {
    const id = nextId++;
    pending[id] = (m) => (m.error ? reject(new Error(m.error.message || "RPC error")) : resolve(m.result));
    post({ id, method, params });
  });
}

function esc(s) { return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function editCellUrl(id, gid, cell) {
  let u = "https://docs.google.com/spreadsheets/d/" + id + "/edit#";
  const f = []; if (gid) f.push("gid=" + gid); if (cell) f.push("range=" + cell); return u + f.join("&");
}
function reviewPanel(flags, id, gid) {
  if (!flags || !flags.length) return '<div class="review"><h2>Review</h2><div class="clean">\\u2713 Nothing flagged for review.</div></div>';
  const items = flags.map(f => '<li><span class="pill ' + esc(f.severity) + '">' + esc(f.severity) + '</span>' +
    '<a class="cell" href="' + editCellUrl(id, gid, f.cell) + '" target="_blank" rel="noopener">' + esc(f.cell) + '</a>' +
    '<span class="why">' + esc(f.reason) + '</span></li>').join("");
  return '<div class="review"><h2>Where to look first (' + flags.length + ')</h2><ul>' + items + '</ul></div>';
}

// SEP-1865: the host delivers the initiating tool's CallToolResult (content +
// structuredContent) via the ui/notifications/tool-result notification.
window.addEventListener("message", (e) => {
  const msg = e.data;
  if (!msg || typeof msg !== "object" || msg.jsonrpc !== JSONRPC) return;
  if (msg.id !== undefined && pending[msg.id]) { pending[msg.id](msg); delete pending[msg.id]; return; }
  if (msg.method === "ui/notifications/tool-result") render(msg.params || {});
});

// SEP-1865 handshake: ui/initialize request. The host validates params and
// requires protocolVersion (string); it returns hostContext. Then announce initialized.
async function init() {
  try {
    await rpc("ui/initialize", {
      appInfo: { name: "Google Sheets MCP App", version: "0.2.0" },
      appCapabilities: {},
      protocolVersion: "2025-06-18",
    });
    post({ method: "ui/notifications/initialized", params: {} });
  } catch (err) { console.error("MCP App init failed:", err); }
}
init();
"""


def render_grid_bridge() -> str:
    """Fixed MCP App UI for the grid tool (meta.ui.resourceUri target)."""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Sheet grid</title><style>{_GRID_CSS}
  #status {{ font-size: 13px; color: #64748b; padding: 8px 0; }}</style></head>
<body>
  <div class="meta" id="hdr"></div>
  <div id="status">Waiting for the host to render the spreadsheet range…</div>
  <div id="review"></div>
  <div id="grid"></div>
<script type="module">
{_BRIDGE_JS}
function render(result) {{
  const d = (result && result.structuredContent) || {{}};
  const values = d.values || [];
  const startRow = d.start_row || 1;
  const flags = d.flags || [];
  document.getElementById("status").style.display = values.length ? "none" : "block";
  const sheet = d.sheet_name ? d.sheet_name + "!" : "";
  $("hdr").innerHTML = "Spreadsheet <b>" + (d.spreadsheet_id || "?") + "</b> &middot; range <b>" +
    sheet + (d.a1_range || "?") + "</b> &middot; sample data" + (d.truncated ? ' <span class="badge">truncated</span>' : "");
  $("review").innerHTML = values.length ? reviewPanel(flags, d.spreadsheet_id || "", "") : "";
  if (!values.length) return;
  const cols = (d.columns || []);
  const byCell = {{}}; flags.forEach(f => byCell[f.cell] = f);
  let html = '<div class="wrap"><table><thead><tr><th class="rowhdr"></th>';
  for (const c of cols) html += "<th>" + c + "</th>";
  html += "</tr></thead><tbody>";
  values.forEach((row, i) => {{
    html += '<tr><th class="rowhdr">' + (startRow + i) + "</th>";
    row.forEach((v, c) => {{
      const a1 = (cols[c] || "") + (startRow + i);
      const f = byCell[a1];
      const cls = f ? ' class="flag-' + esc(f.severity) + '" title="' + esc(f.reason) + '"' : "";
      const dot = f ? '<span class="flagdot">\\u26a0</span>' : "";
      html += "<td" + cls + ">" + esc(v) + dot + "</td>";
    }});
    html += "</tr>";
  }});
  html += "</tbody></table></div>";
  $("grid").innerHTML = html;
}}
</script>
</body></html>"""


def render_embed_bridge() -> str:
    """Fixed MCP App UI for the embed tool (meta.ui.resourceUri target)."""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Live sheet</title><style>
  body {{ font-family: system-ui, sans-serif; margin: 0; padding: 12px; background: #f8fafc; color:#1e293b; }}
  .meta {{ font-size: 12px; color: #64748b; margin-bottom: 8px; }} .meta a {{ color:#2563eb; }}
  #status {{ font-size: 13px; color:#64748b; }}
  .cols {{ display:grid; grid-template-columns:1fr 340px; gap:12px; align-items:start; }}
  @media (max-width:760px) {{ .cols {{ grid-template-columns:1fr; }} }}
  .frame {{ width:100%; height:70vh; min-height:420px; border:1px solid #cbd5e1; border-radius:6px; background:#fff; }}
  iframe {{ width:100%; height:100%; border:0; border-radius:6px; }}
{_GRID_CSS}</style></head>
<body>
  <div class="meta" id="hdr"></div>
  <div id="status">Waiting for the host to provide the spreadsheet to embed…</div>
  <div id="body"></div>
<script type="module">
{_BRIDGE_JS}
function render(result) {{
  const d = (result && result.structuredContent) || {{}};
  if (!d.embed_url) return;
  document.getElementById("status").style.display = "none";
  $("hdr").innerHTML = "Live read-only embed of <b>" + (d.spreadsheet_id || "?") +
    '</b> &middot; <a href="' + (d.edit_url || "#") + '" target="_blank" rel="noopener">open in Google Sheets</a>';
  $("body").innerHTML = '<div class="cols"><div class="frame"><iframe src="' + d.embed_url +
    '" sandbox="allow-scripts allow-same-origin allow-popups" title="Google Sheet preview"></iframe></div>' +
    reviewPanel(d.flags || [], d.spreadsheet_id || "", d.gid || "") + '</div>';
}}
</script>
</body></html>"""


# ---------------------------------------------------------------------------
# Tool output schemas
# ---------------------------------------------------------------------------
class RangePreview(TypedDict):
    spreadsheet_id: str
    a1_range: str
    sheet_name: str
    columns: list[str]
    start_row: int
    values: list[list[str]]
    flags: list[ReviewFlag]
    where_to_look_first: list[str]
    truncated: bool
    edit_url: str
    preview_uri: str


class SheetEmbed(TypedDict):
    spreadsheet_id: str
    gid: str
    embeddable: bool
    edit_url: str
    embed_url: str
    flags: list[ReviewFlag]
    where_to_look_first: list[str]
    preview_uri: str
    note: str


# ---------------------------------------------------------------------------
# Tools (each linked to a UI resource via meta.ui.resourceUri)
# ---------------------------------------------------------------------------
@app.tool(meta={"ui": {"resourceUri": GRID_BRIDGE_URI}})
def render_range_preview(
    spreadsheet_id: Annotated[str, "The Google Sheets spreadsheet id."] = DEFAULT_SAMPLE_SPREADSHEET_ID,
    a1_range: Annotated[str, "A1 range to preview, e.g. 'Sheet1!A1:E10' or 'A1:C20'."] = "A1:E10",
) -> Annotated[dict, "Range values + review flags, plus the ui:// resources that render them."]:
    """Render a spreadsheet range as a reviewable grid (MCP App).

    Returns the (sample) values, the ``flags`` of cells the agent was unsure about
    and a ``where_to_look_first`` list (gap 1), and the ui:// resource URIs. A host
    renders the linked grid UI; ``preview_uri`` is a self-contained HTML grid (with the
    flags highlighted) readable by any MCP client.
    """
    parsed = parse_a1_range(a1_range)
    values = generate_sample_grid(parsed)
    flags = detect_review_flags(parsed, values)
    columns = [_index_to_col(parsed["start_col"] + c) for c in range(parsed["width"])]
    return RangePreview(
        spreadsheet_id=spreadsheet_id,
        a1_range=a1_range,
        sheet_name=parsed["sheet_name"],
        columns=columns,
        start_row=parsed["start_row"],
        values=values,
        flags=flags,
        where_to_look_first=where_to_look_first(flags),
        truncated=parsed["truncated"],
        edit_url=edit_url(spreadsheet_id),
        preview_uri=_grid_preview_uri(spreadsheet_id, a1_range),
    )


@app.tool(meta={"ui": {"resourceUri": EMBED_BRIDGE_URI}})
def render_sheet_embed(
    spreadsheet_id: Annotated[str, "The Google Sheets spreadsheet id."] = DEFAULT_SAMPLE_SPREADSHEET_ID,
    gid: Annotated[str, "Optional sheet/tab gid to focus the embed."] = "",
) -> Annotated[dict, "Embeddable URL + review flags, plus the ui:// resources that frame it."]:
    """Render the live Google Sheet inside an iframe as an MCP App (with gap-1 flags).

    Uses the embeddable ``/preview`` URL (the ``/edit`` URL is X-Frame-Options blocked).
    The iframe only renders sheets the end viewer's browser session can access. The
    ``flags``/``where_to_look_first`` deep-link to the cells to review inside the live sheet.
    """
    parsed = parse_a1_range("A1:E10")
    flags = detect_review_flags(parsed, generate_sample_grid(parsed))
    return SheetEmbed(
        spreadsheet_id=spreadsheet_id,
        gid=gid,
        embeddable=True,
        edit_url=edit_url(spreadsheet_id, gid),
        embed_url=embed_url(spreadsheet_id, gid),
        flags=flags,
        where_to_look_first=where_to_look_first(flags),
        preview_uri=_embed_preview_uri(spreadsheet_id, gid),
        note="Embeds via /preview; renders only sheets viewable in the end user's browser session.",
    )


# ---------------------------------------------------------------------------
# UI resources
# ---------------------------------------------------------------------------
# Fixed "MCP App" UIs — what meta.ui.resourceUri points at. A host renders these
# and pushes the initiating tool result in.
@app.resource(GRID_BRIDGE_URI, name="Sheet grid UI", mime_type="text/html;profile=mcp-app")
def grid_bridge(uri: str) -> str:
    return render_grid_bridge()


# The embed UI frames docs.google.com, so it must declare frame-src via the
# SEP-1865 _meta.ui.csp.frameDomains field, or the host's deny-by-default
# sandbox would block the iframe.
@app.resource(
    EMBED_BRIDGE_URI,
    name="Sheet embed UI",
    mime_type="text/html;profile=mcp-app",
    meta={"ui": {"csp": {"frameDomains": ["https://docs.google.com", "https://*.google.com"]}}},
)
def embed_bridge(uri: str) -> str:
    return render_embed_bridge()


# Static templated UIs — self-contained, data baked in. No Apps host needed; any MCP
# client can resources/read these. Tools return these as preview_uri.
@app.resource(
    "ui://google_sheets_app/grid/{spreadsheet_id}/{a1_range}",
    name="Static sheet grid",
    mime_type="text/html",
)
def grid_static(uri: str, spreadsheet_id: str, a1_range: str) -> str:
    return render_grid_document(unquote(spreadsheet_id), unquote(a1_range))


@app.resource(
    "ui://google_sheets_app/embed/{spreadsheet_id}/{gid}",
    name="Static sheet embed",
    mime_type="text/html",
)
def embed_static(uri: str, spreadsheet_id: str, gid: str) -> str:
    return render_embed_document(unquote(spreadsheet_id), unquote(gid))


if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)
