"""Google Antigravity CLI (agy) adapter.

Locations:
  ~/.gemini/antigravity-cli/brain/<conversation-id>/.system_generated/logs/transcript_full.jsonl
  ~/.gemini/antigravity-cli/history.jsonl   — prompt history, gives the workspace

transcript.jsonl next to it cuts long fields ("truncated_fields"), so the full
transcript is read; the short one only when the full one is missing.

Format: JSONL, one step per line.
  {"step_index": "0", "source": "USER_EXPLICIT", "type": "USER_INPUT",
   "content": "<USER_REQUEST>\\n...\\n</USER_REQUEST>\\n<ADDITIONAL_METADATA>..."}
  {"source": "MODEL", "type": "PLANNER_RESPONSE", "content": "...", "thinking": "...",
   "tool_calls": [{"name": "run_command", "args": {"CommandLine": "...", "Cwd": "C:\\\\..."}}]}
  search_web queries are kept as "[search] ..." lines (a research run may end
  without any text answer); other tool calls, GENERIC (tool output),
  SYSTEM_MESSAGE, ERROR_MESSAGE — skipped.
Only the text inside <USER_REQUEST> is the person's words; the rest of a user step
is metadata the CLI adds (local time, setting changes).

history.jsonl: {"display": "...", "timestamp": ms, "workspace": "C:\\\\...",
                "conversationId": "..."} — the first prompt of a conversation has no
conversationId yet, the following ones do. Without a history entry the workspace
falls back to the most frequent Cwd of the run_command calls.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **_):
        return it

from ..core import Session, mtime_date

AGENT_NAME = "antigravity"
AGY_DIR    = Path.home() / ".gemini" / "antigravity-cli"

_REQUEST = re.compile(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", re.S)


def sessions() -> list[Session]:
    brain = AGY_DIR / "brain"
    if not brain.exists():
        return []
    print("  antigravity: discovering files...", file=sys.stderr, flush=True)
    workspaces = _workspaces()
    result = []
    for conv_dir in tqdm(sorted(p for p in brain.iterdir() if p.is_dir()),
                         desc="  antigravity", unit="conv", leave=False, file=sys.stderr):
        s = _parse(conv_dir, workspaces.get(conv_dir.name, ""))
        if s:
            result.append(s)
    return result


def _workspaces() -> dict[str, str]:
    """conversationId → workspace from history.jsonl."""
    out: dict[str, str] = {}
    try:
        with open(AGY_DIR / "history.jsonl", encoding="utf-8", errors="ignore") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                cid, ws = obj.get("conversationId"), obj.get("workspace")
                if cid and ws:
                    out.setdefault(cid, ws)
    except OSError:
        pass
    return out


def _transcript(conv_dir: Path) -> Path | None:
    logs = conv_dir / ".system_generated" / "logs"
    for name in ("transcript_full.jsonl", "transcript.jsonl"):
        if (logs / name).is_file():
            return logs / name
    return None


def _parse(conv_dir: Path, workspace: str) -> Session | None:
    path = _transcript(conv_dir)
    if not path:
        return None
    turns: list[str] = []
    title = ""
    cwds: Counter = Counter()
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
                kind = obj.get("type", "")
                if kind == "USER_INPUT":
                    text = _user_text(obj.get("content", ""))
                    if text:
                        turns.append(f"[user] {text}")
                        if not title:
                            title = text[:120].replace("\n", " ")
                elif kind == "PLANNER_RESPONSE":
                    text = obj.get("content", "")
                    if isinstance(text, str) and text.strip():
                        turns.append(f"[assistant] {text.strip()}")
                    for call in obj.get("tool_calls") or []:
                        args = (call.get("args") or {}) if isinstance(call, dict) else {}
                        cwd = args.get("Cwd")
                        if isinstance(cwd, str) and cwd:
                            cwds[cwd] += 1
                        # web queries are the searchable trace of a research run
                        # that ended without a text answer (quota, interrupted)
                        if call.get("name") == "search_web" and isinstance(args.get("query"), str):
                            turns.append(f"[search] {args['query'].strip()}")
    except Exception:
        return None

    if not turns:
        return None

    cwd = workspace or (cwds.most_common(1)[0][0] if cwds else "")
    return Session(
        id           = f"antigravity-{conv_dir.name}",
        agent        = AGENT_NAME,
        date         = mtime_date(path),
        project      = Path(cwd).name if cwd else "unknown",
        title        = title or "(untitled)",
        text         = "\n".join(turns),
        source       = str(path),
        resume_cmd   = f"agy --conversation {conv_dir.name}",
        project_path = cwd,
    )


def _user_text(content) -> str:
    if not isinstance(content, str):
        return ""
    m = _REQUEST.search(content)
    return (m.group(1) if m else content).strip()
