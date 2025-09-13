"""
Types and enums for standardized session creation flow.

This module defines the context, modes, options, and results for unified session creation
across all entry points in the application.
"""

from enum import Enum
from typing import NamedTuple, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..chat import ChatSession


class SessionCreationContext(Enum):
    """Different contexts where session creation can occur."""
    APPLICATION_STARTUP = "application_startup"
    MENU_COMMAND = "menu_command"
    SESSION_SWITCH = "session_switch"
    ERROR_RECOVERY = "error_recovery"


class SessionCreationMode(Enum):
    """Different modes of session creation."""
    NEW_SESSION = "new_session"
    LOAD_EXISTING = "load_existing"
    RESUME_SESSION = "resume_session"
    AUTO_DETECT = "auto_detect"


@dataclass
class SessionCreationOptions:
    """Options for session creation."""
    context: SessionCreationContext
    mode: SessionCreationMode
    allow_system_prompt_selection: bool = True
    collect_preferences: bool = True
    show_welcome_message: bool = True
    existing_sessions_available: bool = True


@dataclass
class UserPreferences:
    """User preferences for chat session."""
    markdown_enabled: bool
    show_thinking: bool
    selected_system_prompt: Optional[str] = None


class SessionCreationResult(NamedTuple):
    """Result of session creation process."""
    session: Optional["ChatSession"]
    model: Optional[str]
    preferences: Optional[UserPreferences]
    mode: Optional[SessionCreationMode]
    success: bool
    error_message: Optional[str] = None
