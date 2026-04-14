"""Index sessions from all (or one) agent adapters into ~/.yasna/index/."""
from __future__ import annotations

import os
from pathlib import Path

from .adapters import ALL
from .core import write_session


def _active_cwd(scope: str) -> str | None:
    if scope == "global":
        return None
    cwd  = Path(os.getcwd()).resolve()
    home = Path.home().resolve()
    return str(cwd) if cwd != home else None


def _matches(project_path: str, cwd: str) -> bool:
    if not project_path:
        return True
    pp  = project_path.lower().replace("\\", "/")
    cwd = cwd.lower().replace("\\", "/")
    return pp.startswith(cwd) or cwd.startswith(pp)


def index_all(agent: str | None = None,
              scope: str = "auto") -> dict[str, int | str]:
    """
    scope="auto"   — filter by CWD if not home
    scope="global" — index everything
    """
    adapters   = {k: v for k, v in ALL.items() if agent is None or k == agent}
    active_cwd = _active_cwd(scope)
    stats: dict[str, int | str] = {}

    for name, mod in adapters.items():
        try:
            slist = mod.sessions()
            count = 0
            for s in slist:
                if active_cwd and not _matches(s.project_path, active_cwd):
                    continue
                write_session(s)
                count += 1
            stats[name] = count
        except Exception as e:
            stats[name] = f"ERROR: {e}"

    return stats
