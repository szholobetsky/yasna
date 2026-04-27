"""Index sessions from all (or one) agent adapters into ~/.yasna/index/."""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(it, **_):
        return it

from .adapters import ALL
from .core import INDEX_DIR, read_meta, write_session


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


def _clear_agent_index(name: str, cwd: str | None) -> None:
    agent_dir = INDEX_DIR / name
    if not agent_dir.exists():
        return
    for f in agent_dir.glob("*.txt"):
        if cwd is None:
            f.unlink(missing_ok=True)
        else:
            meta = read_meta(f)
            pp   = meta.get("project_path", "").lower().replace("\\", "/").rstrip("/")
            cwd_n = cwd.lower().replace("\\", "/").rstrip("/")
            if pp == cwd_n or pp.startswith(cwd_n + "/"):
                f.unlink(missing_ok=True)


def index_all(agent: str | None = None,
              scope: str = "auto",
              root: str | None = None) -> dict[str, int | str]:
    """
    scope="auto"   — filter by CWD if not home
    scope="global" — index everything
    """
    adapters   = {k: v for k, v in ALL.items() if agent is None or k == agent}
    if root:
        os.environ["YASNA_SCAN_ROOTS"] = str(Path(root).resolve())
    active_cwd = _active_cwd(scope) if not root else str(Path(root).resolve())
    stats: dict[str, int | str] = {}

    n = len(adapters)
    for i, (name, mod) in enumerate(adapters.items(), 1):
        print(f"[{i}/{n}] {name}", file=sys.stderr, flush=True)
        _clear_agent_index(name, active_cwd)
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
