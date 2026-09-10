"""Pi CLI adapter.

Locations:
  ~/.pi/agent/sessions/<sanitized-cwd>/<timestamp>_<session-id>.jsonl

The sanitized-cwd directory name is not decoded — the real cwd is read from the
session's own first event instead.

Format: JSONL, one event per line.
  {"type": "session", "id": "...", "timestamp": "...", "cwd": "c:\\Projects\\AnimalAlert"}
  {"type": "message", "message": {"role": "user"|"assistant",
                                   "content": [{"type": "text", "text": "..."}, ...]}}
Content blocks of type "thinking"/"toolCall" carry no plain-text field and are skipped.
Other event types (model_change, thinking_level_change, session_info, custom_message, ...)
are metadata/tool-guidance noise and are skipped.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **_):
        return it

from ..core import Session, mtime_date

AGENT_NAME  = "pi"
PI_DIR      = Path.home() / ".pi" / "agent" / "sessions"


def sessions() -> list[Session]:
    if not PI_DIR.exists():
        return []
    print("  pi: discovering files...", file=sys.stderr, flush=True)
    paths = _discover()
    result = []
    for path in tqdm(paths, desc="  pi", unit="file", leave=False, file=sys.stderr):
        s = _parse(path)
        if s:
            result.append(s)
    return result


def _discover() -> list[Path]:
    return sorted(PI_DIR.glob("*/*.jsonl"))


def _parse(path: Path) -> Session | None:
    turns: list[str] = []
    title = ""
    cwd = ""
    session_id = ""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                event_type = obj.get("type", "")

                if event_type == "session":
                    cwd = cwd or obj.get("cwd", "")
                    session_id = session_id or obj.get("id", "")
                    continue

                if event_type != "message":
                    continue

                message = obj.get("message", {})
                role = message.get("role", "")
                if role not in ("user", "assistant"):
                    continue

                content = message.get("content", [])
                text = _extract_text(content)
                if text:
                    turns.append(f"[{role}] {text}")
                    if not title and role == "user":
                        title = text[:120].replace("\n", " ")
    except Exception:
        return None

    if not turns:
        return None

    session_id = session_id or path.stem
    project = Path(cwd).name if cwd else path.parent.name

    return Session(
        id           = f"pi-{session_id}",
        agent        = AGENT_NAME,
        date         = mtime_date(path),
        project      = project,
        title        = title or "(untitled)",
        text         = "\n".join(turns),
        source       = str(path),
        resume_cmd   = f"pi --session {session_id}",
        project_path = cwd,
    )


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return " ".join(
            c.get("text", "") for c in content
            if isinstance(c, dict) and c.get("type") == "text" and c.get("text", "").strip()
        ).strip()
    return ""
