"""aider adapter.

Sessions: ~/.aider.chat.history.md  (global)
          <project>/.aider.chat.history.md  (per-project)

One file contains multiple sessions separated by:
  # aider chat started at YYYY-MM-DD HH:MM:SS
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **_):
        return it

from ..core import Session, scan_roots

AGENT_NAME = "aider"


def sessions() -> list[Session]:
    print("  aider: discovering files...", file=sys.stderr, flush=True)
    files = _discover()
    result = []
    for path in tqdm(files, desc="  aider", unit="file", leave=False, file=sys.stderr):
        result.extend(_parse_file(path))
    return result


def _discover() -> list[Path]:
    found = set()

    # Global history file at home
    global_hist = Path.home() / ".aider.chat.history.md"
    if global_hist.exists():
        found.add(global_hist)

    # Per-project history files under scan roots (depth ≤ 4)
    for root in scan_roots():
        for p in root.glob("**/.aider.chat.history.md"):
            found.add(p)

    return sorted(found)


def _parse_file(path: Path) -> list[Session]:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    sessions_out = []
    # Split on session headers
    blocks = re.split(
        r"(# aider chat started at \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
        content,
    )

    indices = list(range(1, len(blocks) - 1, 2))
    bar = tqdm(indices, desc=f"  {path.name}", unit="session", leave=False, file=sys.stderr)
    for i in bar:
        header = blocks[i]
        body   = blocks[i + 1]
        date_m = re.search(r"(\d{4}-\d{2}-\d{2})", header)
        date   = date_m.group(1) if date_m else mtime_str(path)

        lines  = []
        title  = ""
        for line in body.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            # Skip aider metadata lines
            if stripped.startswith(">") or stripped.startswith("Tokens:"):
                continue
            # User messages start with ####
            if stripped.startswith("####"):
                text = stripped.lstrip("#").strip()
                lines.append(f"[user] {text}")
                if not title:
                    title = text[:120]
            else:
                lines.append(f"[assistant] {stripped}")

        if lines:
            idx = len(sessions_out)
            sessions_out.append(Session(
                id           = f"aider-{date}-{idx}-{path.stem}",
                agent        = AGENT_NAME,
                date         = date,
                project      = path.parent.name,
                title        = title or "(untitled)",
                text         = "\n".join(lines),
                source       = str(path),
                resume_cmd   = f'aider --chat-history-file "{path}"',
                project_path = str(path.parent),
            ))

    return sessions_out


def mtime_str(path: Path) -> str:
    import datetime
    return datetime.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
