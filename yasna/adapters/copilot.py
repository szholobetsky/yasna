"""GitHub Copilot CLI adapter.

Locations:
  ~/.copilot/session-state/<session-id>/events.jsonl   — session event log

Format: JSONL event log, one event per line, real payload nested under "data":
  {"type": "session.start",       "data": {"context": {"cwd": "...", ...}, ...}}
  {"type": "user.message",        "data": {"content": "<plain text>", ...}}
  {"type": "assistant.message",   "data": {"content": "<plain text>", ...}}   — often "" for
                                                                                 tool-only turns
Everything else (model.*, tool.*, permission.*, session.usage_checkpoint, ...) is internal
plumbing with no standalone user-facing text and is skipped.
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

AGENT_NAME   = "copilot"
COPILOT_DIR  = Path.home() / ".copilot"
SESSIONS_DIR = COPILOT_DIR / "session-state"


def sessions() -> list[Session]:
    if not COPILOT_DIR.exists():
        return []
    print("  copilot: discovering files...", file=sys.stderr, flush=True)
    paths = _discover()
    result = []
    for path in tqdm(paths, desc="  copilot", unit="file", leave=False, file=sys.stderr):
        s = _parse(path)
        if s:
            result.append(s)
    return result


def _discover() -> list[Path]:
    if not SESSIONS_DIR.exists():
        return []
    return sorted(SESSIONS_DIR.glob("*/events.jsonl"))


def _parse(path: Path) -> Session | None:
    turns: list[str] = []
    title = ""
    cwd = ""
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
                data = obj.get("data", {})
                if not isinstance(data, dict):
                    continue

                if event_type == "session.start" and not cwd:
                    cwd = data.get("context", {}).get("cwd", "")
                    continue

                if event_type == "user.message":
                    text = data.get("content", "")
                    role = "user"
                elif event_type == "assistant.message":
                    text = data.get("content", "")
                    role = "assistant"
                else:
                    continue

                text = text.strip() if isinstance(text, str) else ""
                if text:
                    turns.append(f"[{role}] {text}")
                    if not title and role == "user":
                        title = text[:120].replace("\n", " ")
    except Exception:
        return None

    if not turns:
        return None

    session_id = path.parent.name
    project = Path(cwd).name if cwd else session_id[:32]

    return Session(
        id           = f"copilot-{session_id}",
        agent        = AGENT_NAME,
        date         = mtime_date(path),
        project      = project,
        title        = title or "(untitled)",
        text         = "\n".join(turns),
        source       = str(path),
        resume_cmd   = f"copilot --resume={session_id}",
        project_path = cwd,
    )
