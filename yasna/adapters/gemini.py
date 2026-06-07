"""Google Gemini CLI adapter.

Two storage formats co-exist:

Old format (.json):
  ~/.gemini/tmp/<project_hash>/chats/session-<TIMESTAMP>-<ID>.json
  Top-level list OR {"history": [...]}
  Message: {"role": "user"|"model", "parts": [{"text": "..."}]}

New format (.jsonl):
  ~/.gemini/tmp/<project_name_or_hash>/chats/session-<TIMESTAMP><ID>.jsonl
  JSONL — one JSON object per line
  First line: {"sessionId": "...", "projectHash": "...", "kind": "main"}
  User:   {"type": "user",   "content": [{"text": "..."}], "timestamp": "..."}
  Gemini: {"type": "gemini", "content": "...", "timestamp": "..."}
  Delta:  {"$set": {...}}  — skip
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

import os

from ..core import Session, mtime_date

AGENT_NAME  = "gemini"
GEMINI_DIR  = Path.home() / ".gemini" / "tmp"

_SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'venv',
              '.tox', 'dist', 'build', '.idea', '.vs', 'target'}


def sessions() -> list[Session]:
    if not GEMINI_DIR.exists():
        return []
    print("  gemini: discovering files...", file=sys.stderr, flush=True)
    paths = _discover()
    result = []
    for path in tqdm(paths, desc="  gemini", unit="file", leave=False, file=sys.stderr):
        s = _parse(path)
        if s:
            result.append(s)
    return result


def _discover() -> list[Path]:
    found: set[Path] = set()
    for ext in ("*.json", "*.jsonl"):
        for p in GEMINI_DIR.glob(f"*/chats/session-{ext}"):
            found.add(p)
    return sorted(found)


def _project_search_roots() -> list[Path]:
    """Roots to search for project directories by name."""
    env = os.environ.get("YASNA_SCAN_ROOTS", "")
    if env:
        return [Path(p) for p in env.split(os.pathsep) if p]
    roots: list[Path] = [Path.cwd()]
    for candidate in (Path("C:/Project"), Path.home() / "Projects",
                      Path.home() / "projects", Path.home() / "dev"):
        if candidate.exists() and candidate not in roots:
            roots.append(candidate)
    return roots


def _resolve_project_path(proj_dir_name: str, max_depth: int = 4) -> str:
    """Find the real filesystem path for a Gemini project dir name (case-insensitive)."""
    name_lower = proj_dir_name.lower()
    # Skip obviously hash-like names (40+ hex chars) — unresolvable
    if len(name_lower) >= 40 and all(c in '0123456789abcdef' for c in name_lower):
        return ""
    # Fast path: cwd itself or its immediate parent
    cwd = Path.cwd()
    if cwd.name.lower() == name_lower:
        return str(cwd)
    # Search configured/common roots
    for root in _project_search_roots():
        result = _find_dir(root, name_lower, max_depth)
        if result:
            return result
    return ""


def _find_dir(base: Path, name_lower: str, depth: int) -> str:
    if depth <= 0:
        return ""
    try:
        for p in base.iterdir():
            if not p.is_dir() or p.name in _SKIP_DIRS or p.name.startswith('.'):
                continue
            if p.name.lower() == name_lower:
                return str(p)
            found = _find_dir(p, name_lower, depth - 1)
            if found:
                return found
    except (PermissionError, OSError):
        pass
    return ""


def _parse(path: Path) -> Session | None:
    if path.suffix == ".jsonl":
        return _parse_jsonl(path)
    return _parse_json(path)


# ── old JSON format ───────────────────────────────────────────────────────────

def _parse_json(path: Path) -> Session | None:
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
    except Exception:
        return None

    if isinstance(data, list):
        history = data
    elif isinstance(data, dict):
        history = data.get("history", data.get("messages", []))
    else:
        return None

    turns = []
    title = ""
    for msg in history:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role", "")
        norm_role = "assistant" if role == "model" else "user"
        parts = msg.get("parts", [])
        text = _extract_parts(parts)
        if text:
            turns.append(f"[{norm_role}] {text}")
            if not title and norm_role == "user":
                title = text[:120].replace("\n", " ")

    if not turns:
        return None

    proj_dir = path.parent.parent.name
    project_path = _resolve_project_path(proj_dir)
    return Session(
        id           = f"gemini-{path.stem}",
        agent        = AGENT_NAME,
        date         = mtime_date(path),
        project      = proj_dir[:32],
        title        = title or "(untitled)",
        text         = "\n".join(turns),
        source       = str(path),
        resume_cmd   = f"gemini  (session: {path.stem})",
        project_path = project_path,
    )


# ── new JSONL format ──────────────────────────────────────────────────────────

def _parse_jsonl(path: Path) -> Session | None:
    turns = []
    title = ""
    date  = ""
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

                # skip delta updates
                if "$set" in obj and len(obj) == 1:
                    continue

                # first-line metadata
                if not session_id and obj.get("sessionId"):
                    session_id = obj["sessionId"]
                if not date and obj.get("startTime"):
                    date = obj["startTime"][:10]

                msg_type = obj.get("type", "")

                if msg_type == "user":
                    content = obj.get("content", [])
                    text = _extract_parts(content) if isinstance(content, list) else str(content).strip()
                    if text:
                        turns.append(f"[user] {text}")
                        if not title:
                            title = text[:120].replace("\n", " ")

                elif msg_type in ("gemini", "assistant", "model"):
                    content = obj.get("content", "")
                    if isinstance(content, str):
                        text = content.strip()
                    elif isinstance(content, list):
                        text = _extract_parts(content)
                    else:
                        text = ""
                    if text:
                        turns.append(f"[assistant] {text}")

    except Exception:
        return None

    if not turns:
        return None

    proj_dir = path.parent.parent.name
    project_path = _resolve_project_path(proj_dir)
    resume_cmd = (f'gemini --resume "{session_id}"' if session_id
                  else f"gemini  (session: {path.stem})")
    return Session(
        id           = f"gemini-{path.stem}",
        agent        = AGENT_NAME,
        date         = date or mtime_date(path),
        project      = proj_dir[:32],
        title        = title or "(untitled)",
        text         = "\n".join(turns),
        source       = str(path),
        resume_cmd   = resume_cmd,
        project_path = project_path,
    )


def _extract_parts(parts) -> str:
    if isinstance(parts, list):
        return " ".join(
            p.get("text", "") for p in parts
            if isinstance(p, dict) and p.get("text", "").strip()
        ).strip()
    if isinstance(parts, str):
        return parts.strip()
    return ""
