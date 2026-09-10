"""Kiro CLI adapter.

Sessions: ~/.kiro/sessions/cli/<uuid>.json   — metadata (cwd, title, timestamps)
          ~/.kiro/sessions/cli/<uuid>.jsonl  — transcript, one JSON event per line

Format (jsonl):
  {"kind": "Prompt",           "data": {"content": [{"kind": "text", "data": "..."}]}}
  {"kind": "AssistantMessage", "data": {"content": [{"kind": "thinking", ...}, {"kind": "text", "data": "..."}]}}
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path, PureWindowsPath

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **_):
        return it

from ..core import Session, mtime_date

AGENT_NAME   = "kiro"
KIRO_DIR     = Path(os.environ.get("KIRO_HOME", str(Path.home() / ".kiro")))
SESSIONS_DIR = KIRO_DIR / "sessions" / "cli"


def sessions() -> list[Session]:
    if not SESSIONS_DIR.exists():
        return []
    print("  kiro: discovering files...", file=sys.stderr, flush=True)
    paths = sorted(SESSIONS_DIR.glob("*.json"))
    result = []
    for path in tqdm(paths, desc="  kiro", unit="file", leave=False, file=sys.stderr):
        s = _parse(path)
        if s:
            result.append(s)
    return result


def _parse(meta_path: Path) -> Session | None:
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    except Exception:
        return None

    session_id = meta.get("session_id", meta_path.stem)
    transcript = meta_path.with_suffix(".jsonl")
    turns = _parse_transcript(transcript)
    if not turns:
        return None

    cwd     = meta.get("cwd", "")
    project = PureWindowsPath(cwd).name if cwd else "unknown"

    created = meta.get("created_at", "")
    date    = created[:10] if len(created) >= 10 else mtime_date(meta_path)

    title = meta.get("title") or turns[0][7:]  # strip "[user] "

    return Session(
        id           = f"kiro-{session_id}",
        agent        = AGENT_NAME,
        date         = date,
        project      = project,
        title        = title[:120].replace("\n", " "),
        text         = "\n".join(turns),
        source       = str(transcript),
        resume_cmd   = f"kiro-cli chat --resume-id {session_id}",
        project_path = cwd,
    )


def _parse_transcript(path: Path) -> list[str]:
    turns: list[str] = []
    if not path.exists():
        return turns
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

                kind = obj.get("kind", "")
                if kind == "Prompt":
                    role = "user"
                elif kind == "AssistantMessage":
                    role = "assistant"
                else:
                    continue

                content = obj.get("data", {}).get("content", [])
                text = " ".join(
                    c.get("data", "") for c in content
                    if isinstance(c, dict) and c.get("kind") == "text" and isinstance(c.get("data"), str)
                ).strip()
                if text:
                    turns.append(f"[{role}] {text}")
    except Exception:
        return []
    return turns
