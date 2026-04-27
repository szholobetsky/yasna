"""yasna CLI.

Usage:
  yasna index [path] [--root DIR] [--agent A] [-g]   # index sessions
  yasna find  <query> [--agent A] [-n N] [-g]         # search sessions
  yasna list  [--agent A] [-n N] [-g]                 # list recent sessions

Examples:
  yasna index                          # current directory, all agents
  yasna index .                        # same
  yasna index D:\\MyProject            # explicit project root
  yasna index --root D:\\MyProject claude  # only claude, specific root
  yasna index -g                       # all agents, no CWD filter
  yasna find "authentication"          # search current project
  yasna find "docker" -g               # search all projects
  yasna find "auth" --agent claude -n 5
"""
from __future__ import annotations

import argparse
import os
import sys


def main():
    # Fix Windows CP1252 terminal — force UTF-8 output
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="yasna",
        description="Session search tool for AI coding agents.",
    )
    sub = parser.add_subparsers(dest="cmd")

    # index
    p_idx = sub.add_parser("index", help="Index sessions from agents")
    p_idx.add_argument(
        "agent", nargs="?", default=None,
        help="Agent to index: claude / opencode / continue / aider / nanocoder / 1bcoder"
             " (or a directory path — auto-detected)",
    )
    p_idx.add_argument("--root", "-r", metavar="DIR", default=None,
                       help="Project root to scan (default: current directory)")
    p_idx.add_argument("--global", "-g", dest="global_scope", action="store_true",
                       help="Index all sessions (ignore CWD filter)")

    # find
    p_find = sub.add_parser("find", help="Search sessions by keyword")
    p_find.add_argument("query", help="Search term")
    p_find.add_argument("--agent", "-a", default=None, help="Filter by agent")
    p_find.add_argument("--limit", "-n", type=int, default=10)
    p_find.add_argument("--global", "-g", dest="global_scope", action="store_true",
                        help="Search all sessions (ignore CWD filter)")

    # about
    sub.add_parser("about", help="Show version and authorship")

    # list
    p_list = sub.add_parser("list", help="List recently indexed sessions")
    p_list.add_argument("--agent", "-a", default=None)
    p_list.add_argument("--limit", "-n", type=int, default=20)
    p_list.add_argument("--global", "-g", dest="global_scope", action="store_true",
                        help="Show all sessions (ignore CWD filter)")

    args = parser.parse_args()

    if args.cmd == "index":
        from .indexer import index_all

        agent = args.agent
        root  = args.root

        # auto-detect: positional looks like a path, not an agent name
        if agent and (os.path.isdir(agent) or agent in (".", "..")):
            root  = agent
            agent = None

        if not root and not os.environ.get("YASNA_SCAN_ROOTS"):
            if sys.platform == "win32":
                example_path = "D:\\MyProject"
                env_example  = "set YASNA_SCAN_ROOTS=D:\\proj1;D:\\proj2"
            else:
                example_path = "/home/user/myproject"
                env_example  = "export YASNA_SCAN_ROOTS=/home/user/proj1:/home/user/proj2"
            print(
                "note: without --root or YASNA_SCAN_ROOTS, local project files\n"
                "      (.1bcoder/, .nanocoder/, .aider.chat.history.md) are scanned\n"
                "      only in the current directory. Global agents (claude, opencode,\n"
                "      continue.dev) are always fully indexed.\n"
               f"      To scan other projects: yasna index {example_path}\n"
               f"      or: {env_example}",
                file=sys.stderr,
            )
        print("Indexing sessions...")
        scope = "global" if args.global_scope else "auto"
        stats = index_all(agent, scope=scope, root=root)
        total = 0
        for name, count in stats.items():
            if isinstance(count, int):
                print(f"  {name:12} {count} session(s)")
                total += count
            else:
                print(f"  {name:12} {count}")
        print(f"\nTotal: {total} session(s) indexed -> ~/.yasna/index/")

    elif args.cmd == "find":
        from .searcher import find as do_find
        scope   = "global" if args.global_scope else "auto"
        results = do_find(args.query, agent=args.agent, limit=args.limit, scope=scope)
        if not results:
            print(f"no matches for: {args.query}")
            sys.exit(1)
        for r in results:
            agent    = r.get("agent", "?")
            date     = r.get("date", "?")
            project  = r.get("project", "?")
            title    = r.get("title", "?")
            resume   = r.get("resume", "")
            proj_path = r.get("project_path", "")
            print(f"\n{agent:10} {date}  [{project}]  {proj_path}")
            print(f"  {title}")
            for s in r.get("snippets", []):
                print(f"  … {s[:130]}")
            if resume:
                print(f"  -> {resume}")

    elif args.cmd == "list":
        from .searcher import list_sessions
        scope    = "global" if args.global_scope else "auto"
        sessions = list_sessions(agent=args.agent, limit=args.limit, scope=scope)
        if not sessions:
            print("No sessions indexed. Run: yasna index")
            sys.exit(1)
        for s in sessions:
            agent     = s.get("agent", "?")
            date      = s.get("date", "?")
            project   = s.get("project", "?")
            title     = s.get("title", "?")
            proj_path = s.get("project_path", "")
            print(f"{agent:10} {date}  [{project}]  {proj_path}")
            print(f"  {title}")

    elif args.cmd == "about":
        print("yasna — Session search tool for AI coding agents")
        print()
        print("(c) 2026 Stanislav Zholobetskyi")
        print("Institute for Information Recording, National Academy of Sciences of Ukraine, Kyiv")
        print("PhD research: \u00abIntelligent Technology for Software Development and Maintenance Support\u00bb")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
