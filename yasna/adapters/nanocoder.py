"""nanocoder adapter.

Checkpoints: <project>/.nanocoder/checkpoints/<name>/conversation.json
Format:      JSON array of {role, content}
Note:        Checkpoints are created manually with /checkpoint create <name>
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

from ..core import Session, mtime_date, scan_roots

AGENT_NAME = "nanocoder"


def sessions() -> list[Session]:
    print("  nanocoder: discovering files...", file=sys.stderr, flush=True)
    paths = _discover()
    result = []
    for path in tqdm(paths, desc="  nanocoder", unit="file", leave=False, file=sys.stderr):
        s = _parse(path)
        if s:
            result.append(s)
    return result


def _discover() -> list[Path]:
    found = set()
    for root in scan_roots():
        for p in root.glob("**/.nanocoder/checkpoints/*/conversation.json"):
            found.add(p)
    return sorted(found)


def _parse(path: Path) -> Session | None:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    if not isinstance(data, list):
        return None

    turns = []
    title = ""
    for msg in data:
        role    = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            text = " ".join(
                c.get("text", "") for c in content if isinstance(c, dict)
            ).strip()
        else:
            text = str(content).strip()

        if text:
            turns.append(f"[{role}] {text}")
            if not title and role == "user":
                title = text[:120]

    if not turns:
        return None

    checkpoint_name = path.parent.name
    # path: <proj>/.nanocoder/checkpoints/<name>/conversation.json
    project = path.parts[-5] if len(path.parts) >= 5 else path.parent.parent.parent.parent.name

    # path: <proj>/.nanocoder/checkpoints/<name>/conversation.json  → proj = 4 levels up
    proj_dir = path.parent.parent.parent.parent

    return Session(
        id           = f"nanocoder-{checkpoint_name}",
        agent        = AGENT_NAME,
        date         = mtime_date(path),
        project      = project,
        title        = title or checkpoint_name,
        text         = "\n".join(turns),
        source       = str(path),
        resume_cmd   = f"/checkpoint load {checkpoint_name}",
        project_path = str(proj_dir),
    )
