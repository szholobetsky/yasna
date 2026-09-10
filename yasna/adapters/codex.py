"""OpenAI Codex CLI adapter.

Locations:
  ~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<session-id>.jsonl   — per-session logs

Format (current, CLI v0.154+): JSONL, one event per line.
  {"type": "session_meta", "payload": {"session_id": "...", "cwd": "..."}}
  {"type": "response_item", "payload": {"type": "message", "role": "user"|"assistant"|"developer",
                                          "content": [{"type": "input_text"|"output_text", "text": "..."}]}}
Other payload types (custom_tool_call, reasoning, ...) carry no plain text and are skipped.
"~/.codex/history.jsonl" (user prompts only, no assistant replies) is intentionally not used —
its content is a strict subset of the rollout files.

Note: does NOT honor a $CODEX_HOME override — other tools (e.g. multi-agent orchestrators) have
been observed setting that env var globally to redirect Codex into a sandboxed runtime directory
that holds no real session history. The genuine session store is always at ~/.codex/sessions/.
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
CODEX_DIR  = Path.home() / ".codex"


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
    return sorted((CODEX_DIR / "sessions").glob("**/rollout-*.jsonl"))


def _parse(path: Path) -> Session | None:
    turns: list[str] = []
    title = ""
    cwd = ""
    session_id = ""
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

                if obj.get("type") == "session_meta":
                    meta = obj.get("payload", {})
                    cwd = cwd or meta.get("cwd", "")
                    session_id = session_id or meta.get("session_id", "")
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

    project    = Path(cwd).name if cwd else path.parent.name
    session_id = session_id or path.stem

    return Session(
        id           = f"codex-{session_id}",
        agent        = AGENT_NAME,
        date         = date,
        project      = project,
        title        = title or "(untitled)",
        text         = "\n".join(turns),
        source       = str(path),
        resume_cmd   = f"codex resume {session_id}",
        project_path = cwd,
    )


def _extract(obj: dict) -> tuple[str, str]:
    """Return (text, role) from a response_item message event; ("", "") for anything else."""
    if obj.get("type") != "response_item":
        return "", ""

    payload = obj.get("payload", {})
    if payload.get("type") != "message":
        return "", ""

    role = payload.get("role", "")
    if role not in ("user", "assistant"):
        return "", ""

    content = payload.get("content", [])
    if isinstance(content, list):
        text = " ".join(
            c.get("text", "") for c in content
            if isinstance(c, dict) and c.get("text", "").strip()
        ).strip()
    elif isinstance(content, str):
        text = content.strip()
    else:
        text = ""

    # synthetic environment-context block injected by the CLI itself, not the human
    if role == "user" and text.startswith("<environment_context>"):
        return "", ""

    return text, role
