"""OpenAI Codex CLI adapter.

Locations:
  ~/.codex/history.jsonl                         — rolling history
  ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl   — per-session logs

Format: JSONL. Two relevant event types:
  {"type": "user_message", "message": "<text>"}
  {"type": "message", "role": "assistant", "content": [{"type":"output_text","text":"..."}]}
  {"role": "user"|"assistant", "content": "..."}   — simpler variant
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

AGENT_NAME = "codex"
CODEX_DIR  = Path(
    __import__("os").environ.get("CODEX_HOME", str(Path.home() / ".codex"))
)


def sessions() -> list[Session]:
    if not CODEX_DIR.exists():
        return []
    print("  codex: discovering files...", file=sys.stderr, flush=True)
    paths = _discover()
    result = []
    for path in tqdm(paths, desc="  codex", unit="file", leave=False, file=sys.stderr):
        s = _parse(path)
        if s:
            result.append(s)
    return result


def _discover() -> list[Path]:
    found = set()
    h = CODEX_DIR / "history.jsonl"
    if h.exists():
        found.add(h)
    for p in (CODEX_DIR / "sessions").glob("**/rollout-*.jsonl"):
        found.add(p)
    return sorted(found)


def _parse(path: Path) -> Session | None:
    turns: list[str] = []
    title = ""
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

                text, role = _extract(obj)
                if text:
                    turns.append(f"[{role}] {text}")
                    if not title and role == "user":
                        title = text[:120].replace("\n", " ")
    except Exception:
        return None

    if not turns:
        return None

    # derive date from path YYYY/MM/DD or mtime
    date = mtime_date(path)
    parts = path.parts
    for i, p in enumerate(parts):
        if p.isdigit() and len(p) == 4 and i + 2 < len(parts):
            try:
                date = f"{p}-{parts[i+1].zfill(2)}-{parts[i+2].zfill(2)}"
            except Exception:
                pass
            break

    sid = f"codex-{path.stem}-{abs(hash(str(path))) % 100000}"
    return Session(
        id           = sid,
        agent        = AGENT_NAME,
        date         = date,
        project      = path.parent.name,
        title        = title or "(untitled)",
        text         = "\n".join(turns),
        source       = str(path),
        resume_cmd   = f"codex  (log: {path.name})",
        project_path = "",
    )


def _extract(obj: dict) -> tuple[str, str]:
    """Return (text, role) from any known event shape."""
    # shape 1: {"type": "user_message", "message": "..."}
    if obj.get("type") == "user_message":
        return obj.get("message", "").strip(), "user"

    # shape 2: {"type": "message", "role": "...", "content": [...]}
    if obj.get("type") == "message" or "role" in obj:
        role = obj.get("role", "assistant")
        norm = "assistant" if role == "assistant" else "user"
        content = obj.get("content", "")
        if isinstance(content, str):
            return content.strip(), norm
        if isinstance(content, list):
            text = " ".join(
                c.get("text", "") for c in content
                if isinstance(c, dict) and c.get("text", "").strip()
            ).strip()
            return text, norm

    return "", "user"
