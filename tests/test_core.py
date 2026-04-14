"""Tests for yasna.core — session write/read round-trip."""
import pytest
from yasna.core import Session, write_session, read_meta, session_path


@pytest.fixture
def sample_session():
    return Session(
        id="test-session-001",
        agent="claude",
        date="2026-04-14",
        project="simrgl",
        title="svitovyd mcp setup",
        text="[user] how to setup mcp\n[assistant] use FastMCP",
        source="/home/user/.claude/projects/test/test.jsonl",
        resume_cmd="claude --resume test-session-001",
        project_path="C:/Project/simrgl",
    )


def test_write_creates_file(sample_session, tmp_path, monkeypatch):
    monkeypatch.setattr("yasna.core.INDEX_DIR", tmp_path / "index")
    path = write_session(sample_session)
    assert path.exists()


def test_read_meta_returns_agent(sample_session, tmp_path, monkeypatch):
    monkeypatch.setattr("yasna.core.INDEX_DIR", tmp_path / "index")
    path = write_session(sample_session)
    meta = read_meta(path)
    assert meta["agent"] == "claude"


def test_read_meta_round_trip(sample_session, tmp_path, monkeypatch):
    monkeypatch.setattr("yasna.core.INDEX_DIR", tmp_path / "index")
    path = write_session(sample_session)
    meta = read_meta(path)
    assert meta["date"] == "2026-04-14"
    assert meta["project"] == "simrgl"
    assert meta["title"] == "svitovyd mcp setup"
    assert meta["project_path"] == "C:/Project/simrgl"


def test_write_preserves_text(sample_session, tmp_path, monkeypatch):
    monkeypatch.setattr("yasna.core.INDEX_DIR", tmp_path / "index")
    path = write_session(sample_session)
    content = path.read_text(encoding="utf-8")
    assert "FastMCP" in content
    assert "[user]" in content


def test_session_path_uses_agent(sample_session, tmp_path, monkeypatch):
    monkeypatch.setattr("yasna.core.INDEX_DIR", tmp_path / "index")
    path = session_path(sample_session)
    assert "claude" in str(path)
