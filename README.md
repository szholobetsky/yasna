![yasna](images/yasna.png)

# yasna

Session search tool for AI coding agents.

Indexes conversation history from Claude Code, opencode, continue.dev, aider, nanocoder, and 1bcoder into a single searchable store — so you can find any session by keyword, resume it instantly, and never lose track of what you discussed and where.

```bash
yasna find "myapp mcp"
```
```
claude     2026-04-10  [myapp]  D:\Work\myapp
  myapp mcp server, FastMCP tools...
  … map_index, map_find, BFS trace deps sym idiff
  -> claude --resume cc3cf9f6-6ce9-46d0-9e70-ce2b6354a975

opencode   2026-04-08  [myapp]  D:\Work\myapp
  myapp mcp endpoint discussion
  -> opencode  (session: ses_2ed3ba03...)
```

---

## The problem

Every AI coding agent stores its sessions differently — or not at all. After a few weeks of active work you have dozens of conversations scattered across JSONL files, SQLite databases, markdown logs, and JSON checkpoints. You remember discussing something important about authentication, or a deployment fix, or a refactoring decision — but you do not remember which tool, which project, or which day.

yasna solves this in one command.

---

## Supported agents

| Agent | Storage | Sessions |
|---|---|---|
| Claude Code | `~/.claude/projects/**/*.jsonl` | full conversations, auto |
| opencode | `~/.local/share/opencode/opencode.db` | full conversations, auto |
| continue.dev | `~/.continue/sessions/*.json` | full conversations, auto |
| aider | `~/.aider.chat.history.md` + `<project>/.aider.chat.history.md` | full conversations, auto |
| nanocoder | `<project>/.nanocoder/checkpoints/*/conversation.json` | manual (`/checkpoint create`) |
| 1bcoder | `~/.1bcoder/` + `<project>/.1bcoder/` | context files (`/ctx save`, autosave) |

Agents that do not store sessions locally (GitHub Copilot, Windsurf, Augment, Amazon Q) are not supported — there is nothing to index.

---

## Installation

```bash
pip install yasna
```

No heavy dependencies. Requires Python 3.10+. Uses only stdlib (sqlite3, pathlib, json, re).

---

## Quick start

```bash
# Index current project (all agents)
yasna index

# Index a specific directory
yasna index D:\MyProject

# Index everything, no CWD filter
yasna index -g

# Search current project
yasna find "authentication middleware"
yasna find "docker compose"

# Search all projects
yasna find "MAP@10" -g

# Filter by agent
yasna find "migration" --agent claude
yasna list --agent opencode

# List recently indexed sessions
yasna list
yasna list -g -n 50
```

---

## CWD-aware filtering

yasna knows which project you are working in. When run from a project directory, it automatically filters results to sessions from that project only.

```bash
# From ~/Project/myapp:
yasna find "auth"       # only myapp sessions
yasna find "auth" -g    # all sessions from all projects

# From ~/ (home directory):
yasna find "auth"       # all sessions (no filter)
```

Same for indexing:

```bash
# From ~/Project/myapp:
yasna index             # index only myapp sessions
yasna index -g          # index everything
```

This keeps personal and work projects separate without any configuration.

---

## Commands

### `yasna index [path] [-r DIR] [-a agent] [-g]`

Scan all agents (or one) and write indexed sessions to `~/.yasna/index/`.

```bash
yasna index                        # current directory, all agents
yasna index .                      # same
yasna index D:\MyProject           # explicit project root
yasna index claude                 # Claude Code only, current directory
yasna index -g                     # all agents, no CWD filter
yasna index -g claude              # Claude Code only, no filter
yasna index --root D:\MyProject claude   # claude only, explicit root
```

The positional argument is auto-detected: if it looks like a directory path it sets the scan root; if it is an agent name it filters by agent. Use `--root`/`-r` when you need both.

Run this periodically or after finishing a work session. Each run clears and rewrites the index for the current project (or globally with `-g`), so there are no stale duplicates.

### `yasna find <query> [-a agent] [-n N] [-g]`

Search indexed sessions for a keyword. Returns up to N results (default 10) with matching context snippets and resume commands.

```bash
yasna find "pgvector"
yasna find "FastMCP" --agent claude
yasna find "init wizard" -n 5
yasna find "book crossing" -g    # ignore CWD filter
```

### `yasna list [-a agent] [-n N] [-g]`

List the most recently indexed sessions (default 20).

```bash
yasna list
yasna list --agent aider
yasna list -n 50 -g
```

---

## Scan roots

Global agent storage is always scanned automatically:
- `~/.claude/projects/` — Claude Code
- `~/.local/share/opencode/opencode.db` — opencode
- `~/.continue/sessions/` — continue.dev
- `~/.aider.chat.history.md` — aider (global log)
- `~/.1bcoder/` — 1bcoder (global ctx, autosave, projects)

For project-local files (`.aider.chat.history.md`, `.nanocoder/`, `.1bcoder/` inside a project), yasna scans the **current working directory** by default.

To scan a different or additional directory pass it as an argument or set an environment variable:

```bash
# Explicit path argument
yasna index D:\MyProject
yasna index --root D:\MyProject

# Multiple roots via environment variable (path-separator-separated)
# Windows
set YASNA_SCAN_ROOTS=C:\Projects\rubocop;D:\Work\client-app
yasna index -g

# Linux / macOS
export YASNA_SCAN_ROOTS=/home/user/projects:/mnt/work
yasna index -g
```

---

## Adding a new adapter

Each agent adapter is a single Python file in `yasna/adapters/` that exposes:

```python
AGENT_NAME: str

def sessions() -> list[Session]:
    ...
```

Drop a new file in that directory and register it in `yasna/adapters/__init__.py`:

```python
from . import my_new_agent

ALL: dict = {
    ...
    "mynewagent": my_new_agent,
}
```

That is all. The CLI, indexer, and searcher need no changes.

---

## Part of the SIMARGL toolkit

yasna is one of four tools that together form an **intellectual development support system**:

| Tool | Role |
|---|---|
| **[simargl](https://github.com/szholobetsky/simargl)** | Task-to-code retrieval — given a task description, finds which files and modules are likely affected, using semantic similarity over git history |
| **[svitovyd](https://github.com/szholobetsky/svitovyd)** | Project map — scans any codebase and produces a structural map of definitions and cross-file dependencies; exposes it as an MCP server |
| **[1bcoder](https://github.com/szholobetsky/1bcoder)** | AI coding assistant for small local models — surgical context management, agents, parallel inference, proc scripts |
| **[yasna](https://github.com/szholobetsky/yasna)** | Session memory — indexes conversations from all AI agents so you can find what was discussed, when, and where |

- **simargl** answers: *what code is related to this task?*
- **svitovyd** answers: *how is the code structured and what depends on what?*
- **1bcoder** answers: *how do I work with local models efficiently?*
- **yasna** answers: *where did I already discuss this?*

Together they cover the full development loop: understand the codebase, find relevant history, work with AI locally, remember what was decided.

The name comes from Slavic mythology. Yasna (Ясна) is the goddess who weaves the thread of fate — and memory.

---

## About

(c) 2026 Stanislav Zholobetskyi  
Institute for Information Recording, National Academy of Sciences of Ukraine, Kyiv  
PhD research: «Intelligent Technology for Software Development and Maintenance Support»
