"""Adapter registry.

Each adapter module exposes:
    AGENT_NAME: str
    def sessions() -> list[Session]
"""
from . import claude, opencode, continue_dev, aider, nanocoder, one_bcoder
from . import gemini, codex, copilot, kiro, pi, antigravity

ALL: dict = {
    "claude":    claude,
    "opencode":  opencode,
    "continue":  continue_dev,
    "aider":     aider,
    "nanocoder": nanocoder,
    "1bcoder":   one_bcoder,
    "gemini":    gemini,
    "codex":     codex,
    "copilot":   copilot,
    "kiro":      kiro,
    "pi":        pi,
    "antigravity": antigravity,
}
