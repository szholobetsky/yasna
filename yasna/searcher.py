"""Search indexed sessions by keyword."""
from __future__ import annotations

import os
import re
from pathlib import Path

from .core import INDEX_DIR, read_meta


def _cwd_filter() -> str | None:
    """Return current directory if it's not home — used to auto-filter results."""
    cwd  = Path(os.getcwd()).resolve()
    home = Path.home().resolve()
    return str(cwd) if cwd != home else None


def _matches_project(meta: dict, cwd: str) -> bool:
    """True if session's project_path overlaps with cwd."""
    pp = meta.get("project_path", "").strip()
    if not pp:
        return True   # no project_path stored → include (don't hide)
    pp_lower  = pp.lower().replace("\\", "/")
    cwd_lower = cwd.lower().replace("\\", "/")
    return pp_lower.startswith(cwd_lower) or cwd_lower.startswith(pp_lower)


def find(query: str, agent: str | None = None, limit: int = 20,
         scope: str | None = "auto") -> list[dict]:
    """
    scope="auto"   — filter by CWD if not home (default)
    scope="global" — show all sessions regardless of CWD
    scope=<path>   — filter by that path explicitly
    """
    if not INDEX_DIR.exists():
        return []

    if scope == "auto":
        active_cwd = _cwd_filter()
    elif scope == "global":
        active_cwd = None
    else:
        active_cwd = scope

    pattern    = re.compile(re.escape(query), re.IGNORECASE)
    search_dir = INDEX_DIR / agent if agent else INDEX_DIR
    results    = []

    for path in sorted(
        search_dir.glob("**/*.txt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # Split header / body
        if "---\n" in content:
            header_part, body = content.split("---\n", 1)
        else:
            header_part, body = content, ""

        meta = read_meta(path)

        if active_cwd and not _matches_project(meta, active_cwd):
            continue

        if not (pattern.search(body) or pattern.search(meta.get("title", ""))):
            continue

        # Collect up to 3 matching lines with one line of context each
        body_lines = body.splitlines()
        snippets   = []
        for i, line in enumerate(body_lines):
            if pattern.search(line):
                ctx = body_lines[max(0, i - 1): i + 2]
                snippets.append(" | ".join(l.strip() for l in ctx if l.strip()))
            if len(snippets) >= 3:
                break

        results.append({**meta, "snippets": snippets})
        if len(results) >= limit:
            break

    return results


def list_sessions(agent: str | None = None, limit: int = 20,
                  scope: str | None = "auto") -> list[dict]:
    if not INDEX_DIR.exists():
        return []

    if scope == "auto":
        active_cwd = _cwd_filter()
    elif scope == "global":
        active_cwd = None
    else:
        active_cwd = scope

    search_dir = INDEX_DIR / agent if agent else INDEX_DIR
    all_paths  = sorted(
        search_dir.glob("**/*.txt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    results = []
    for p in all_paths:
        if len(results) >= limit:
            break
        meta = read_meta(p)
        if active_cwd and not _matches_project(meta, active_cwd):
            continue
        results.append(meta)

    return results
