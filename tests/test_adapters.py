"""Tests for yasna adapters — each adapter parsed with synthetic fixture data."""
import json
import pytest
from pathlib import Path


# ── aider adapter ─────────────────────────────────────────────────────────────

def test_aider_parses_history(tmp_path):
    from yasna.adapters.aider import _parse_file
    hist = tmp_path / ".aider.chat.history.md"
    hist.write_text(
        "# aider chat started at 2026-04-01 10:00:00\n\n"
        "> Aider v1.0\n\n"
        "#### how do I fix login?\n\n"
        "You should validate input.\n\n"
        "> Tokens: 100 sent, 20 received.\n",
        encoding="utf-8",
    )
    sessions = _parse_file(hist)
    assert len(sessions) == 1
    assert sessions[0].date == "2026-04-01"
    assert "login" in sessions[0].title.lower() or "login" in sessions[0].text


def test_aider_multiple_sessions(tmp_path):
    from yasna.adapters.aider import _parse_file
    hist = tmp_path / ".aider.chat.history.md"
    hist.write_text(
        "# aider chat started at 2026-04-01 10:00:00\n\n#### first question\n\nAnswer one.\n"
        "# aider chat started at 2026-04-02 11:00:00\n\n#### second question\n\nAnswer two.\n",
        encoding="utf-8",
    )
    sessions = _parse_file(hist)
    assert len(sessions) == 2


# ── continue.dev adapter ──────────────────────────────────────────────────────

def test_continue_parses_session(tmp_path):
    from yasna.adapters.continue_dev import _parse
    session_file = tmp_path / "abc123.json"
    data = {
        "sessionId": "abc123",
        "title": "Explain authentication",
        "workspaceDirectory": "file:///c%3A/Project/simrgl",
        "history": [
            {"message": {"role": "user", "content": [{"type": "text", "text": "How does login work?"}]}},
            {"message": {"role": "assistant", "content": [{"type": "text", "text": "It uses JWT tokens."}]}},
        ],
    }
    session_file.write_text(json.dumps(data), encoding="utf-8")
    s = _parse(session_file)
    assert s is not None
    assert s.agent == "continue"
    assert "JWT" in s.text
    assert s.project == "simrgl"


def test_continue_skips_empty_history(tmp_path):
    from yasna.adapters.continue_dev import _parse
    f = tmp_path / "empty.json"
    f.write_text(json.dumps({"sessionId": "x", "history": []}), encoding="utf-8")
    assert _parse(f) is None


# ── nanocoder adapter ─────────────────────────────────────────────────────────

def test_nanocoder_parses_checkpoint(tmp_path):
    from yasna.adapters.nanocoder import _parse
    proj = tmp_path / "myproject" / ".nanocoder" / "checkpoints" / "my-checkpoint"
    proj.mkdir(parents=True)
    conv = proj / "conversation.json"
    conv.write_text(json.dumps([
        {"role": "user", "content": "How do I fix the auth module?"},
        {"role": "assistant", "content": "Check the login function."},
    ]), encoding="utf-8")
    s = _parse(conv)
    assert s is not None
    assert "auth" in s.text
    assert s.id == "nanocoder-my-checkpoint"


def test_nanocoder_skips_invalid_json(tmp_path):
    from yasna.adapters.nanocoder import _parse
    proj = tmp_path / "p" / ".nanocoder" / "checkpoints" / "bad"
    proj.mkdir(parents=True)
    f = proj / "conversation.json"
    f.write_text("not json", encoding="utf-8")
    assert _parse(f) is None


# ── 1bcoder adapter ───────────────────────────────────────────────────────────

def test_one_bcoder_parses_ctx_file(tmp_path, monkeypatch):
    from yasna.adapters import one_bcoder
    monkeypatch.setattr(one_bcoder, "BCODER_HOME", tmp_path / ".1bcoder")
    monkeypatch.setattr(one_bcoder, "scan_roots", lambda: [tmp_path])
    ctx_dir = tmp_path / ".1bcoder" / "ctx"
    ctx_dir.mkdir(parents=True)
    (ctx_dir / "auth_context.txt").write_text(
        "Authentication module context\nHandles login and JWT tokens.\n",
        encoding="utf-8",
    )
    sessions = one_bcoder.sessions()
    assert len(sessions) == 1
    assert "JWT" in sessions[0].text
