"""1bcoder adapter.

Context files (not conversations — 1bcoder doesn't persist chat history):
  ~/.1bcoder/ctx/           — global context library
  ~/.1bcoder/projects/<k>/  — per-project saved contexts
  <project>/.1bcoder/ctx/   — local project ctx

Each .txt/.md file is indexed as a separate "session".
"""
from __future__ import annotations

from pathlib import Path

from ..core import Session, mtime_date, scan_roots

AGENT_NAME  = "1bcoder"
BCODER_HOME = Path.home() / ".1bcoder"


def sessions() -> list[Session]:
    result = []
    for path in _discover():
        s = _parse(path)
        if s:
            result.append(s)
    return result


def _discover() -> list[Path]:
    found = set()

    # Global ctx
    for p in (BCODER_HOME / "ctx").glob("*"):
        if p.suffix in (".txt", ".md") and p.is_file():
            found.add(p)

    # Per-project ctx at ~/.1bcoder/projects/
    for p in (BCODER_HOME / "projects").glob("*/*"):
        if p.suffix in (".txt", ".md") and p.is_file() and p.name != "project.txt":
            found.add(p)

    # Local .1bcoder/ctx/ under scan roots
    for root in scan_roots():
        for p in root.glob("**/.1bcoder/ctx/*"):
            if p.suffix in (".txt", ".md") and p.is_file():
                found.add(p)
        for p in root.glob("**/.1bcoder/projects/*/*"):
            if p.suffix in (".txt", ".md") and p.is_file() and p.name != "project.txt":
                found.add(p)
        for p in root.glob("**/.1bcoder/autosave/*"):
            if p.suffix in (".txt", ".md") and p.is_file():
                found.add(p)

    # Global autosave
    for p in (BCODER_HOME / "autosave").glob("*"):
        if p.suffix in (".txt", ".md") and p.is_file():
            found.add(p)

    return sorted(found)


def _parse(path: Path) -> Session | None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
    except Exception:
        return None

    if not text:
        return None

    # Determine project name from path
    parts = path.parts
    if "projects" in parts:
        idx     = list(parts).index("projects")
        project = parts[idx + 1] if idx + 1 < len(parts) else "default"
    elif "ctx" in parts:
        # Find what project this ctx belongs to
        # .1bcoder/ctx/ → global; <proj>/.1bcoder/ctx/ → project name
        try:
            bcoder_idx = list(parts).index(".1bcoder")
            project    = parts[bcoder_idx - 1] if bcoder_idx > 0 else "global"
        except ValueError:
            project = "global"
    else:
        project = path.parent.name

    title = text.split("\n")[0][:120].strip()
    sid   = f"1bcoder-{path.stem}-{abs(hash(str(path))) % 100000}"

    # project dir = the dir that contains .1bcoder/
    try:
        bcoder_idx = list(path.parts).index(".1bcoder")
        proj_dir   = str(Path(*path.parts[:bcoder_idx]))
    except ValueError:
        proj_dir   = str(path.parent)

    return Session(
        id           = sid,
        agent        = AGENT_NAME,
        date         = mtime_date(path),
        project      = project,
        title        = title or path.name,
        text         = text,
        source       = str(path),
        resume_cmd   = f"/ctx load {path.name}",
        project_path = proj_dir,
    )
