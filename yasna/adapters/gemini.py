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

from ..core import Session, mtime_date

AGENT_NAME  = "gemini"
GEMINI_DIR  = Path.home() / ".gemini" / "tmp"


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

    proj_hash = path.parent.parent.name
    return Session(
        id           = f"gemini-{path.stem}",
        agent        = AGENT_NAME,
        date         = mtime_date(path),
        project      = proj_hash[:32],
        title        = title or "(untitled)",
        text         = "\n".join(turns),
        source       = str(path),
        resume_cmd   = f"gemini  (session: {path.stem})",
        project_path = "",
    )


# ── new JSONL format ──────────────────────────────────────────────────────────

def _parse_jsonl(path: Path) -> Session | None:
    turns = []
    title = ""
    date  = ""
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

                msg_type = obj.get("type", "")

                # first-line metadata — grab date
                if not date and obj.get("startTime"):
                    date = obj["startTime"][:10]

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
    return Session(
        id           = f"gemini-{path.stem}",
        agent        = AGENT_NAME,
        date         = date or mtime_date(path),
        project      = proj_dir[:32],
        title        = title or "(untitled)",
        text         = "\n".join(turns),
        source       = str(path),
        resume_cmd   = f"gemini  (session: {path.stem})",
        project_path = "",
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
