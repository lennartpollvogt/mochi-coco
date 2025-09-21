"""
Configuration structures for tool settings with backward compatibility.

This module defines configuration classes and enums for managing tool settings
in chat sessions, including execution policies and tool selection.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

class ToolExecutionPolicy(Enum):
    """Policy for tool execution confirmation."""
    ALWAYS_CONFIRM = "always_confirm"
    NEVER_CONFIRM = "never_confirm"
    CONFIRM_DESTRUCTIVE = "confirm_destructive"  # Future enhancement

@dataclass
class ToolSettings:
    """Tool settings for a session."""
    tools: List[str] = field(default_factory=list)
    tool_group: Optional[str] = None
    execution_policy: ToolExecutionPolicy = ToolExecutionPolicy.ALWAYS_CONFIRM

    def __post_init__(self):
        # Handle legacy confirmation_necessary field for backward compatibility
        # Note: We can't delete the property, so we just ensure the execution_policy
        # is set correctly based on any legacy data that might be present
        pass

    @property
    def confirmation_necessary(self) -> bool:
        """Backward compatibility property."""
        return self.execution_policy == ToolExecutionPolicy.ALWAYS_CONFIRM

    def is_enabled(self) -> bool:
        """Check if any tools are enabled."""
        return bool(self.tools or self.tool_group)

    def get_active_tools(self, all_tools: Dict[str, Any],
                         tool_groups: Dict[str, List[str]]) -> List[str]:
        """Get list of active tool names based on settings."""
        if self.tool_group and self.tool_group in tool_groups:
            return tool_groups[self.tool_group]
        return self.tools

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for session storage."""
        return {
            'tools': self.tools,
            'tool_group': self.tool_group,
            'execution_policy': self.execution_policy.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolSettings':
        """Create from dictionary (session storage)."""
        # Handle legacy confirmation_necessary field
        if 'confirmation_necessary' in data and 'execution_policy' not in data:
            if data['confirmation_necessary']:
                data['execution_policy'] = ToolExecutionPolicy.ALWAYS_CONFIRM.value
            else:
                data['execution_policy'] = ToolExecutionPolicy.NEVER_CONFIRM.value
            del data['confirmation_necessary']

        # Convert execution_policy string to enum
        if 'execution_policy' in data and isinstance(data['execution_policy'], str):
            data['execution_policy'] = ToolExecutionPolicy(data['execution_policy'])

        return cls(**data)
