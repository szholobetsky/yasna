---
title: "yasna: A Unified Session Search Tool for AI Coding Agents"
authors:
  - name: Stanislav Zholobetskyi
    orcid: 0009-0008-6058-7233
    affiliation: 1
affiliations:
  - name: Institute for Information Recording, Kyiv, Ukraine
    index: 1
date: 2026-04-14
bibliography: paper.bib
---

# Summary

`yasna` is a command-line tool that indexes conversation sessions from multiple AI coding agents — Claude Code, opencode, continue.dev, aider, nanocoder, and 1bcoder — into a single searchable plain-text store. It allows developers to search past sessions by keyword, retrieve the context of a specific discussion, and obtain the exact command needed to resume that session in the originating tool. A working-directory-aware filtering mechanism automatically scopes results to the current project without explicit configuration.

# Statement of need

AI-assisted software development increasingly involves multiple specialized tools used in parallel or in succession. Each tool stores conversation history in its own format: JSONL files (Claude Code), SQLite databases (opencode), JSON session files (continue.dev), Markdown logs (aider), or manual checkpoints (nanocoder). Some tools store nothing at all. As a result, the institutional knowledge embedded in past sessions — architectural decisions, debugging rationale, design alternatives discussed and rejected — is inaccessible unless the developer remembers exactly which tool and which day.

This problem intensifies in research contexts where a developer may run dozens of experimental sessions exploring different approaches to the same problem. The inability to search across sessions creates redundant exploration and makes reproducibility of reasoning difficult.

`yasna` addresses this by normalising heterogeneous session stores into a single indexed format and exposing a uniform keyword search interface. The tool requires no server, no database engine, and no embeddings — sessions are stored as annotated plain-text files queryable with standard string matching. A plugin architecture based on per-agent adapter modules makes it straightforward to add support for new tools as they emerge.

# Functionality

**Indexing** (`yasna index`): scans all configured agent stores, parses each session format via a dedicated adapter, and writes normalised plain-text files to `~/.yasna/index/<agent>/`. Each file contains a metadata header (`agent`, `date`, `project`, `project_path`, `resume` command) followed by the full conversation text. CWD-aware filtering limits indexing to sessions whose recorded project path matches the current working directory, keeping project namespaces separate by default. The `--global` flag disables this filter.

**Search** (`yasna find`): performs case-insensitive keyword search over indexed files and returns matching sessions with context snippets and resume commands. Respects the same CWD filter as indexing.

**Listing** (`yasna list`): lists the most recently indexed sessions, optionally filtered by agent.

**Adapter architecture**: each agent adapter is a single Python module exposing one function (`sessions() -> list[Session]`). Adding support for a new agent requires no changes to the core indexer, searcher, or CLI — only a new module and a one-line registration entry.

# Related software

No existing tool provides unified cross-agent session search for AI coding tools. MemPalace [@mempalace] offers a vector-based long-term memory system accessible via MCP but requires explicit memory ingestion and is designed for agent-mediated recall rather than human-directed search. `yasna` is complementary: it serves as a feeder that can populate such systems. Shell history managers (e.g., `atuin` [@atuin]) address command history, not AI conversation history.

# Acknowledgements

This work is conducted as part of a PhD research programme at the Institute for Information Recording, Kyiv, Ukraine.

# References
