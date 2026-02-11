"""
Configuration structures for agent settings with serialization helpers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentSettings:
    """
    Agent settings for a session.

    Attributes:
        enabled_agents: List of enabled agent names.
        selection_metadata: Optional metadata for UI/selection state.
    """

    enabled_agents: List[str] = field(default_factory=list)
    selection_metadata: Optional[Dict[str, Any]] = None

    def is_enabled(self) -> bool:
        """Return True if at least one agent is enabled."""
        return bool(self.enabled_agents)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for session storage."""
        return {
            "enabled_agents": list(self.enabled_agents),
            "selection_metadata": self.selection_metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentSettings":
        """Create from dictionary (session storage)."""
        enabled = data.get("enabled_agents", [])
        metadata = data.get("selection_metadata")
        if enabled is None:
            enabled = []
        return cls(enabled_agents=list(enabled), selection_metadata=metadata)
