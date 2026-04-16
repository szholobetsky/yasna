# yasna

Session search tool for AI coding agents.

Indexes conversation history from Claude Code, opencode, continue.dev, aider, nanocoder, and 1bcoder into a single searchable store — so you can find any session by keyword, resume it instantly, and never lose track of what you discussed and where.

```bash
yasna find "svitovyd mcp"
```
```
claude     2026-04-10  [simrgl]  "svitovyd mcp server, FastMCP tools..."
           ... | map_index, map_find, BFS trace deps sym idiff
           -> claude --resume cc3cf9f6-6ce9-46d0-9e70-ce2b6354a975

opencode   2026-04-08  [svitovyd]  "map_index endpoint discussion"
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
| aider | `**/.aider.chat.history.md` | full conversations, auto |
| nanocoder | `**/.nanocoder/checkpoints/*/conversation.json` | manual (`/checkpoint create`) |
| 1bcoder | `.1bcoder/ctx/` and `.1bcoder/projects/*/` | context files |

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
# Index all sessions (scans all supported agents)
yasna index

# Search across indexed sessions
yasna find "authentication middleware"
yasna find "docker compose"
yasna find "MAP@10"

# List recently indexed sessions
yasna list

# Filter by agent
yasna find "migration" --agent claude
yasna list --agent opencode
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

### `yasna index [agent] [-g]`

Scan all agents (or one) and write indexed sessions to `~/.yasna/index/`.

```bash
yasna index                  # all agents, CWD filter
yasna index claude           # Claude Code only
yasna index -g               # all agents, no filter
yasna index opencode -g      # opencode only, no filter
```

Run this periodically or after finishing a work session. Indexing is fast — it re-writes all sessions each time (no incremental tracking yet).

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

By default yasna scans:
- `~/.claude/projects/` — Claude Code (global, fixed)
- `~/.local/share/opencode/opencode.db` — opencode (global, fixed)
- `~/.continue/sessions/` — continue.dev (global, fixed)
- `~/` and `C:/Project/` — for aider, nanocoder, 1bcoder (recursive glob)

To add more project roots (e.g. `D:/Work`), set the environment variable:

```bash
# Windows
set YASNA_SCAN_ROOTS=C:\Project;D:\Work\clients

# Linux / macOS
export YASNA_SCAN_ROOTS=/home/user/projects:/mnt/work
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
