"""Adapter registry.

Each adapter module exposes:
    AGENT_NAME: str
    def sessions() -> list[Session]
"""
from . import claude, opencode, continue_dev, aider, nanocoder, one_bcoder

ALL: dict = {
    "claude":    claude,
    "opencode":  opencode,
    "continue":  continue_dev,
    "aider":     aider,
    "nanocoder": nanocoder,
    "1bcoder":   one_bcoder,
}
