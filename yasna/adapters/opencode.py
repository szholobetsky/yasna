"""opencode adapter.

Sessions: ~/.local/share/opencode/opencode.db  (SQLite)
Tables:   session + part (joined by session_id)
"""
from __future__ import annotations

import datetime
import json
import sqlite3
from pathlib import Path

from ..core import Session

AGENT_NAME  = "opencode"
OPENCODE_DB = Path.home() / ".local" / "share" / "opencode" / "opencode.db"


def sessions() -> list[Session]:
    if not OPENCODE_DB.exists():
        return []
    result = []
    try:
        con = sqlite3.connect(f"file:{OPENCODE_DB}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT s.id, s.title, s.directory, s.time_created "
            "FROM session s ORDER BY s.time_created"
        ).fetchall()

        for sid, title, directory, time_created in rows:
            parts = con.execute(
                "SELECT m.data, p.data FROM part p "
                "JOIN message m ON p.message_id = m.id "
                "WHERE p.session_id = ? ORDER BY p.time_created",
                (sid,),
            ).fetchall()

            turns = []
            for msg_data_str, part_data_str in parts:
                try:
                    role = json.loads(msg_data_str).get("role", "?")
                    part = json.loads(part_data_str)
                    if part.get("type") == "text" and part.get("text", "").strip():
                        turns.append(f"[{role}] {part['text'].strip()}")
                except Exception:
                    pass

            if not turns:
                continue

            date    = datetime.datetime.fromtimestamp(time_created / 1000).strftime("%Y-%m-%d")
            project = Path(directory).name if directory else "unknown"
            t       = (title or turns[0][7:])[:120].replace("\n", " ")

            result.append(Session(
                id           = sid,
                agent        = AGENT_NAME,
                date         = date,
                project      = project,
                title        = t,
                text         = "\n".join(turns),
                source       = str(OPENCODE_DB),
                resume_cmd   = f"opencode  (session: {sid})",
                project_path = directory or "",
            ))
        con.close()
    except Exception:
        pass
    return result
