"""GitHub Copilot CLI adapter.

Locations:
  ~/.copilot/session-state/<session-id>/events.jsonl   — current session logs
  ~/.copilot/history-session-state/<session-id>/events.jsonl  — legacy (auto-migrated)

Format: JSONL event log. Relevant event types:
  {"type": "user_message",   "message": "..."}
  {"type": "agent_message",  "message": "..."}   or  "response"/"assistant_message"
  {"type": "message",        "role": "user"|"assistant", "content": "..."}
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

_SESSION_ROOTS = [
    COPILOT_DIR / "session-state",
    COPILOT_DIR / "history-session-state",
]


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
    found: set[Path] = set()
    for root in _SESSION_ROOTS:
        if root.exists():
            for p in root.glob("**/events.jsonl"):
                found.add(p)
    return sorted(found)


def _parse(path: Path) -> Session | None:
    turns: list[str] = []
    title = ""
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

                text, role = _extract(obj)
                if text:
                    turns.append(f"[{role}] {text}")
                    if not title and role == "user":
                        title = text[:120].replace("\n", " ")
    except Exception:
        return None

    if not turns:
        return None

    # session-id is the parent directory name
    session_id_dir = path.parent.name
    sid = f"copilot-{session_id_dir[:24]}"

    return Session(
        id           = sid,
        agent        = AGENT_NAME,
        date         = mtime_date(path),
        project      = session_id_dir[:32],
        title        = title or "(untitled)",
        text         = "\n".join(turns),
        source       = str(path),
        resume_cmd   = f"gh copilot  (session: {session_id_dir[:16]})",
        project_path = "",
    )


def _extract(obj: dict) -> tuple[str, str]:
    """Return (text, role) from any known Copilot event shape."""
    event_type = obj.get("type", "")

    # user message variants
    if event_type in ("user_message", "human_message"):
        return obj.get("message", "").strip(), "user"

    # assistant/agent message variants
    if event_type in ("agent_message", "assistant_message", "response", "copilot_message"):
        msg = obj.get("message", obj.get("content", obj.get("text", "")))
        return msg.strip() if isinstance(msg, str) else "", "assistant"

    # generic {"type": "message", "role": "...", "content": "..."}
    if event_type == "message" or "role" in obj:
        role = obj.get("role", "assistant")
        norm = "assistant" if role in ("assistant", "model", "copilot") else "user"
        content = obj.get("content", obj.get("message", ""))
        if isinstance(content, str):
            return content.strip(), norm
        if isinstance(content, list):
            text = " ".join(
                c.get("text", "") for c in content
                if isinstance(c, dict) and c.get("text", "").strip()
            ).strip()
            return text, norm

    return "", "user"
