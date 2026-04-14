"""Tests for yasna.searcher — find and list over indexed sessions."""
import pytest
from yasna.core import Session, write_session
from yasna.searcher import find, list_sessions


@pytest.fixture
def indexed_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr("yasna.core.INDEX_DIR", tmp_path / "index")
    monkeypatch.setattr("yasna.searcher.INDEX_DIR", tmp_path / "index")

    sessions = [
        Session("id-1", "claude", "2026-04-01", "simrgl",
                "svitovyd mcp setup",
                "[user] how to setup mcp server\n[assistant] use FastMCP and pip install",
                "/path/a.jsonl", "claude --resume id-1", "C:/Project/simrgl"),
        Session("id-2", "opencode", "2026-04-02", "book-crossing",
                "book recommendation algorithm",
                "[user] implement collaborative filtering\n[assistant] use matrix factorization",
                "/db/opencode.db", "opencode (session: id-2)", "C:/Project/book-crossing"),
        Session("id-3", "aider", "2026-04-03", "simrgl",
                "fix login bug",
                "[user] login fails with special chars\n[assistant] escape the input",
                "/path/history.md", "aider --chat-history-file /path/history.md", "C:/Project/simrgl"),
    ]
    for s in sessions:
        write_session(s)
    return tmp_path


def test_find_returns_match(indexed_sessions):
    results = find("FastMCP", scope="global")
    assert len(results) >= 1
    assert any("FastMCP" in str(r) or "svitovyd" in r.get("title", "") for r in results)


def test_find_no_match(indexed_sessions):
    results = find("xyznonexistent123", scope="global")
    assert results == []


def test_find_cwd_filter(indexed_sessions):
    results = find("login", scope="C:/Project/simrgl")
    assert all(
        r.get("project_path", "").replace("\\", "/").startswith("C:/Project/simrgl")
        or not r.get("project_path")
        for r in results
    )
    assert not any(r.get("project") == "book-crossing" for r in results)


def test_find_global_shows_all_agents(indexed_sessions):
    results = find("login", scope="global")
    agents = {r.get("agent") for r in results}
    assert len(agents) >= 1


def test_list_sessions_returns_all(indexed_sessions):
    sessions = list_sessions(scope="global", limit=10)
    assert len(sessions) == 3


def test_list_sessions_filter_by_agent(indexed_sessions):
    sessions = list_sessions(agent="claude", scope="global")
    assert all(s.get("agent") == "claude" for s in sessions)


def test_find_limit_respected(indexed_sessions):
    results = find("login", scope="global", limit=1)
    assert len(results) <= 1
