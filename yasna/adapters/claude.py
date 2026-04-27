"""Claude Code adapter.

Sessions: ~/.claude/projects/<project_dir>/<uuid>.jsonl
Format:   JSONL — each line is a message object
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

AGENT_NAME  = "claude"
CLAUDE_DIR  = Path.home() / ".claude" / "projects"


def sessions() -> list[Session]:
    if not CLAUDE_DIR.exists():
        return []
    paths = [p for p in CLAUDE_DIR.glob("**/*.jsonl") if "subagents" not in p.parts]
    result = []
    for path in tqdm(paths, desc="  claude", unit="file", leave=False, file=sys.stderr):
        s = _parse(path)
        if s:
            result.append(s)
    return result


def _parse(path: Path) -> Session | None:
    session_id = path.stem
    proj_raw   = path.parent.name          # e.g. "C--Project-codeXplorer-capestone-simrgl"
    project    = proj_raw.split("-")[-1]   # "simrgl"

    turns        = []
    title        = ""
    date         = ""
    project_path = ""

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

                msg_type = obj.get("type", "")

                # Skip non-message entries
                if msg_type in ("file-history-snapshot", "summary", "system"):
                    continue

                # Timestamp + cwd from first message
                if not date and obj.get("timestamp"):
                    date = obj["timestamp"][:10]
                if not project_path and obj.get("cwd"):
                    project_path = obj["cwd"]

                # Extract role + content
                msg = obj.get("message", obj)
                role = msg.get("role", msg_type) or msg_type
                if role not in ("user", "assistant", "human"):
                    continue

                text = _extract_content(msg.get("content", ""))
                if not text:
                    continue

                turns.append(f"[{role}] {text}")
                if not title and role in ("user", "human"):
                    title = text[:120].replace("\n", " ")

    except Exception:
        return None

    if not turns:
        return None

    return Session(
        id           = session_id,
        agent        = AGENT_NAME,
        date         = date or mtime_date(path),
        project      = project,
        title        = title or "(untitled)",
        text         = "\n".join(turns),
        source       = str(path),
        resume_cmd   = f"claude --resume {session_id}",
        project_path = project_path,
    )


def _extract_content(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
                elif item.get("type") == "tool_result":
                    # skip tool results to keep text clean
                    pass
            elif isinstance(item, str):
                parts.append(item)
        return " ".join(p for p in parts if p).strip()
    return ""
