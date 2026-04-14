"""Core data model and index storage."""
from __future__ import annotations

import datetime
import os
from dataclasses import dataclass
from pathlib import Path

YASNA_DIR = Path.home() / ".yasna"
INDEX_DIR  = YASNA_DIR / "index"

# Additional directories to scan for session files (aider, nanocoder, etc.)
# Override via YASNA_SCAN_ROOTS env var (colon-separated paths)
def scan_roots() -> list[Path]:
    env = os.environ.get("YASNA_SCAN_ROOTS", "")
    if env:
        return [Path(p) for p in env.split(os.pathsep) if p]
    # Defaults: home + C:\Project if exists
    roots = [Path.home()]
    if Path("C:/Project").exists():
        roots.append(Path("C:/Project"))
    return roots


@dataclass
class Session:
    id:           str
    agent:        str
    date:         str        # YYYY-MM-DD
    project:      str
    title:        str        # first user message, truncated
    text:         str        # full conversation text for search
    source:       str        # original file/db path
    resume_cmd:   str        # how to open/resume this session
    project_path: str = ""   # absolute filesystem path of the project (for CWD filter)


def session_path(s: Session) -> Path:
    safe_id = s.id.replace("/", "_").replace("\\", "_").replace(":", "_")
    return INDEX_DIR / s.agent / f"{safe_id}.txt"


def write_session(s: Session) -> Path:
    path = session_path(s)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f":::agent: {s.agent}\n")
        f.write(f":::date: {s.date}\n")
        f.write(f":::project: {s.project}\n")
        f.write(f":::title: {s.title}\n")
        f.write(f":::source: {s.source}\n")
        f.write(f":::resume: {s.resume_cmd}\n")
        f.write(f":::project_path: {s.project_path}\n")
        f.write("---\n")
        f.write(s.text)
    return path


def mtime_date(path: Path) -> str:
    ts = path.stat().st_mtime
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def read_meta(path: Path) -> dict:
    meta = {}
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("---"):
                    break
                if line.startswith(":::"):
                    k, _, v = line[3:].rstrip().partition(": ")
                    meta[k] = v
    except Exception:
        pass
    return meta
