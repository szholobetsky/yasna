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


# ── kiro adapter ──────────────────────────────────────────────────────────────

def test_kiro_parses_session(tmp_path):
    from yasna.adapters.kiro import _parse
    meta_path = tmp_path / "sess1.json"
    meta_path.write_text(json.dumps({
        "session_id": "sess1",
        "cwd": "C:\\Projects\\myapp",
        "created_at": "2026-09-08T21:04:35.368719600Z",
        "title": None,
    }), encoding="utf-8")
    jsonl_path = tmp_path / "sess1.jsonl"
    jsonl_path.write_text(
        json.dumps({"kind": "Prompt", "data": {"content": [{"kind": "text", "data": "how does login work?"}]}}) + "\n"
        + json.dumps({"kind": "AssistantMessage", "data": {"content": [
            {"kind": "thinking", "data": {"text": ""}},
            {"kind": "text", "data": "It uses JWT tokens."},
        ]}}) + "\n",
        encoding="utf-8",
    )
    s = _parse(meta_path)
    assert s is not None
    assert s.agent == "kiro"
    assert s.project == "myapp"
    assert s.date == "2026-09-08"
    assert "JWT" in s.text
    assert "login" in s.title.lower()
    assert "sess1" in s.resume_cmd


def test_kiro_skips_empty_transcript(tmp_path):
    from yasna.adapters.kiro import _parse
    meta_path = tmp_path / "sess2.json"
    meta_path.write_text(json.dumps({"session_id": "sess2", "cwd": "C:\\Users\\stasz"}), encoding="utf-8")
    (tmp_path / "sess2.jsonl").write_text("", encoding="utf-8")
    assert _parse(meta_path) is None


# ── codex adapter ─────────────────────────────────────────────────────────────

def test_codex_parses_rollout(tmp_path):
    from yasna.adapters.codex import _parse
    rollout = tmp_path / "rollout-2026-09-10T22-16-47-01a08cc0-4933.jsonl"
    lines = [
        {"type": "session_meta", "payload": {"session_id": "01a08cc0-4933", "cwd": "C:\\Projects\\myapp"}},
        {"type": "response_item", "payload": {"type": "message", "role": "developer",
            "content": [{"type": "input_text", "text": "system instructions"}]}},
        {"type": "response_item", "payload": {"type": "message", "role": "user",
            "content": [{"type": "input_text", "text": "<environment_context><cwd>C:\\Projects\\myapp</cwd></environment_context>"}]}},
        {"type": "response_item", "payload": {"type": "message", "role": "user",
            "content": [{"type": "input_text", "text": "how does login work?"}]}},
        {"type": "response_item", "payload": {"type": "custom_tool_call", "id": "x"}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant",
            "content": [{"type": "output_text", "text": "It uses JWT tokens."}]}},
    ]
    rollout.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
    s = _parse(rollout)
    assert s is not None
    assert s.agent == "codex"
    assert s.project == "myapp"
    assert "JWT" in s.text
    assert "environment_context" not in s.text
    assert "login" in s.title.lower()
    assert s.resume_cmd == "codex resume 01a08cc0-4933"


def test_codex_skips_session_with_only_environment_context(tmp_path):
    from yasna.adapters.codex import _parse
    rollout = tmp_path / "rollout-empty.jsonl"
    lines = [
        {"type": "session_meta", "payload": {"session_id": "empty1", "cwd": "C:\\Users\\stasz"}},
        {"type": "response_item", "payload": {"type": "message", "role": "user",
            "content": [{"type": "input_text", "text": "<environment_context>only this</environment_context>"}]}},
    ]
    rollout.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
    assert _parse(rollout) is None


# ── copilot adapter ───────────────────────────────────────────────────────────

def test_copilot_parses_events(tmp_path):
    from yasna.adapters.copilot import _parse
    session_dir = tmp_path / "session-state" / "abc123"
    session_dir.mkdir(parents=True)
    events = session_dir / "events.jsonl"
    lines = [
        {"type": "session.start", "data": {"context": {"cwd": "C:\\Projects\\myapp"}}},
        {"type": "session.model_change", "data": {"newModel": "gpt-5-mini"}},
        {"type": "user.message", "data": {"content": "how does login work?"}},
        {"type": "tool.execution_start", "data": {"toolName": "read_file"}},
        {"type": "assistant.message", "data": {"content": ""}},
        {"type": "assistant.message", "data": {"content": "It uses JWT tokens."}},
    ]
    events.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
    s = _parse(events)
    assert s is not None
    assert s.agent == "copilot"
    assert s.project == "myapp"
    assert "JWT" in s.text
    assert "login" in s.title.lower()
    assert s.resume_cmd == "copilot --resume=abc123"


def test_copilot_skips_session_with_no_messages(tmp_path):
    from yasna.adapters.copilot import _parse
    session_dir = tmp_path / "session-state" / "empty1"
    session_dir.mkdir(parents=True)
    events = session_dir / "events.jsonl"
    lines = [{"type": "session.start", "data": {"context": {"cwd": "C:\\Users\\stasz"}}}]
    events.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
    assert _parse(events) is None


# ── pi adapter ────────────────────────────────────────────────────────────────

def test_pi_parses_session(tmp_path):
    from yasna.adapters.pi import _parse
    session_dir = tmp_path / "--C--Projects-myapp--"
    session_dir.mkdir(parents=True)
    session_file = session_dir / "2026-08-21T16-05-37-079Z_abc123.jsonl"
    lines = [
        {"type": "session", "id": "abc123", "timestamp": "2026-08-21T16:05:37.079Z", "cwd": "c:\\Projects\\myapp"},
        {"type": "model_change", "provider": "ollama", "modelId": "qwen2.5-coder:7b"},
        {"type": "message", "message": {"role": "user",
            "content": [{"type": "text", "text": "how does login work?"}]}},
        {"type": "message", "message": {"role": "assistant",
            "content": [{"type": "thinking", "text": "let me check"},
                        {"type": "toolCall", "id": "c1", "name": "read", "arguments": {}},
                        {"type": "text", "text": "It uses JWT tokens."}]}},
    ]
    session_file.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
    s = _parse(session_file)
    assert s is not None
    assert s.agent == "pi"
    assert s.project == "myapp"
    assert "JWT" in s.text
    assert "login" in s.title.lower()
    assert s.resume_cmd == "pi --session abc123"


def test_pi_skips_session_with_no_messages(tmp_path):
    from yasna.adapters.pi import _parse
    session_dir = tmp_path / "--C--Users-stasz--"
    session_dir.mkdir(parents=True)
    session_file = session_dir / "2026-08-21T16-05-37-079Z_empty1.jsonl"
    lines = [{"type": "session", "id": "empty1", "cwd": "c:\\Users\\stasz"}]
    session_file.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
    assert _parse(session_file) is None


# ── antigravity adapter ───────────────────────────────────────────────────────

def _agy_conv(root, cid, steps):
    logs = root / "brain" / cid / ".system_generated" / "logs"
    logs.mkdir(parents=True)
    (logs / "transcript_full.jsonl").write_text(
        "\n".join(json.dumps(s, ensure_ascii=False) for s in steps), encoding="utf-8")
    return root / "brain" / cid


def test_antigravity_parses_conversation(tmp_path, monkeypatch):
    from yasna.adapters import antigravity
    monkeypatch.setattr(antigravity, "AGY_DIR", tmp_path)
    _agy_conv(tmp_path, "c1", [
        {"step_index": "0", "source": "USER_EXPLICIT", "type": "USER_INPUT",
         "content": "<USER_REQUEST>\nhow to use sqlfluff?\n</USER_REQUEST>\n"
                    "<ADDITIONAL_METADATA>\nThe current local time is: 2026-10-24T11:28:00+03:00.\n</ADDITIONAL_METADATA>"},
        {"step_index": "1", "source": "MODEL", "type": "PLANNER_RESPONSE",
         "tool_calls": [{"name": "run_command", "args": {"CommandLine": "dir", "Cwd": "C:\Other"}},
                        {"name": "search_web", "args": {"query": "sqlfluff dbt templater"}}]},
        {"step_index": "2", "source": "MODEL", "type": "GENERIC", "content": "Command output: noise"},
        {"step_index": "3", "source": "MODEL", "type": "PLANNER_RESPONSE", "content": "SQLFluff is a SQL linter."},
    ])
    (tmp_path / "history.jsonl").write_text("\n".join(json.dumps(h) for h in [
        {"display": "how to use sqlfluff?", "timestamp": 1, "workspace": "C:\Projects\shop"},
        {"display": "and dbt?", "timestamp": 2, "workspace": "C:\Projects\shop", "conversationId": "c1"},
    ]), encoding="utf-8")
    [s] = antigravity.sessions()
    assert s.agent == "antigravity"
    assert s.title == "how to use sqlfluff?"
    assert s.project == "shop" and s.project_path == "C:\Projects\shop"
    assert "SQLFluff is a SQL linter." in s.text
    assert "[search] sqlfluff dbt templater" in s.text
    assert "ADDITIONAL_METADATA" not in s.text and "noise" not in s.text
    assert s.resume_cmd == "agy --conversation c1"


def test_antigravity_workspace_falls_back_to_cwd(tmp_path, monkeypatch):
    from yasna.adapters import antigravity
    monkeypatch.setattr(antigravity, "AGY_DIR", tmp_path)
    _agy_conv(tmp_path, "c2", [
        {"type": "USER_INPUT", "content": "<USER_REQUEST>\nfind papers\n</USER_REQUEST>"},
        {"type": "PLANNER_RESPONSE", "tool_calls": [{"name": "run_command", "args": {"Cwd": "C:\Projects\MZVO"}}]},
        {"type": "ERROR_MESSAGE", "error": "RESOURCE_EXHAUSTED (code 429)"},
    ])
    [s] = antigravity.sessions()
    assert s.project == "MZVO"
    assert "429" not in s.text


def test_antigravity_skips_conversation_without_transcript(tmp_path, monkeypatch):
    from yasna.adapters import antigravity
    monkeypatch.setattr(antigravity, "AGY_DIR", tmp_path)
    (tmp_path / "brain" / "c3" / "scratch").mkdir(parents=True)
    assert antigravity.sessions() == []
