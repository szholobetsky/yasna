"""yasna CLI.

Usage:
  yasna index [agent]                    # index all agents (or one)
  yasna find <query> [--agent A] [-n N]  # search sessions
  yasna list [--agent A] [-n N]          # list recent sessions
"""
from __future__ import annotations

import argparse
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
        help="Agent to index: claude / opencode / continue / aider / nanocoder / 1bcoder",
    )
    p_idx.add_argument("--global", "-g", dest="global_scope", action="store_true",
                       help="Index all sessions (ignore CWD filter)")

    # find
    p_find = sub.add_parser("find", help="Search sessions by keyword")
    p_find.add_argument("query", help="Search term")
    p_find.add_argument("--agent", "-a", default=None, help="Filter by agent")
    p_find.add_argument("--limit", "-n", type=int, default=10)
    p_find.add_argument("--global", "-g", dest="global_scope", action="store_true",
                        help="Search all sessions (ignore CWD filter)")

    # list
    p_list = sub.add_parser("list", help="List recently indexed sessions")
    p_list.add_argument("--agent", "-a", default=None)
    p_list.add_argument("--limit", "-n", type=int, default=20)
    p_list.add_argument("--global", "-g", dest="global_scope", action="store_true",
                        help="Show all sessions (ignore CWD filter)")

    args = parser.parse_args()

    if args.cmd == "index":
        from .indexer import index_all
        print("Indexing sessions...")
        scope = "global" if args.global_scope else "auto"
        stats = index_all(args.agent, scope=scope)
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
            agent   = r.get("agent", "?")
            date    = r.get("date", "?")
            project = r.get("project", "?")
            title   = r.get("title", "?")
            resume  = r.get("resume", "")
            print(f"\n{agent:10} {date}  [{project}]  {title}")
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
            agent   = s.get("agent", "?")
            date    = s.get("date", "?")
            project = s.get("project", "?")
            title   = s.get("title", "?")
            print(f"{agent:10} {date}  [{project}]  {title}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
