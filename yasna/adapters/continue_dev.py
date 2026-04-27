"""continue.dev adapter.

Sessions: ~/.continue/sessions/<uuid>.json
Format:   JSON with history[].message.{role, content[]}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import unquote

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **_):
        return it

from ..core import Session, mtime_date

AGENT_NAME    = "continue"
CONTINUE_DIR  = Path.home() / ".continue" / "sessions"


def sessions() -> list[Session]:
    if not CONTINUE_DIR.exists():
        return []
    print("  continue: discovering files...", file=sys.stderr, flush=True)
    paths = [p for p in CONTINUE_DIR.glob("*.json") if p.name != "sessions.json"]
    result = []
    for path in tqdm(paths, desc="  continue", unit="file", leave=False, file=sys.stderr):
        s = _parse(path)
        if s:
            result.append(s)
    return result


def _parse(path: Path) -> Session | None:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    session_id = data.get("sessionId", path.stem)
    title      = data.get("title", "")
    workspace  = data.get("workspaceDirectory", "")

    # "file:///c%3A/Project/simrgl" → "simrgl"
    if workspace:
        clean = unquote(workspace).replace("file:///", "").replace("file://", "")
        project = Path(clean).name
    else:
        project = "unknown"

    turns = []
    for entry in data.get("history", []):
        msg     = entry.get("message", {})
        role    = msg.get("role", "")
        content = msg.get("content", [])

        if isinstance(content, list):
            text = " ".join(
                c.get("text", "") for c in content
                if isinstance(c, dict) and c.get("type") == "text"
            ).strip()
        elif isinstance(content, str):
            text = content.strip()
        else:
            text = ""

        if text:
            turns.append(f"[{role}] {text}")

    if not turns:
        return None

    title_text = title or turns[0][7:]   # strip "[user] "
    ws_path = unquote(workspace).replace("file:///", "").replace("file://", "") if workspace else ""

    return Session(
        id           = session_id,
        agent        = AGENT_NAME,
        date         = mtime_date(path),
        project      = project,
        title        = title_text[:120].replace("\n", " "),
        text         = "\n".join(turns),
        source       = str(path),
        resume_cmd   = f"open in continue.dev  (id: {session_id})",
        project_path = ws_path,
    )
