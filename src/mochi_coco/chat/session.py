import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class Message:
    role: str
    content: str
    timestamp: str | None = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class SessionMetadata:
    session_id: str
    model: str
    created_at: str
    updated_at: str
    message_count: int = 0


class ChatSession:
    def __init__(self, model: str, session_id: Optional[str] = None, sessions_dir: Optional[str] = None):
        self.model = model
        self.session_id = session_id or self._generate_session_id()
        self.sessions_dir = Path(sessions_dir) if sessions_dir else Path.cwd() / "chat_sessions"
        self.sessions_dir.mkdir(exist_ok=True)

        self.messages: List[Message] = []
        self.metadata = SessionMetadata(
            session_id=self.session_id,
            model=model,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )

        # Try to load existing session
        if session_id:
            self.load_session()

    def _generate_session_id(self) -> str:
        """Generate a random 10-character session ID using UUID."""
        return str(uuid.uuid4()).replace("-", "")[:10]

    @property
    def session_file(self) -> Path:
        """Get the path to the session JSON file."""
        return self.sessions_dir / f"{self.session_id}.json"

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the session."""
        message = Message(role=role, content=content)
        self.messages.append(message)
        self.metadata.message_count = len(self.messages)
        self.metadata.updated_at = datetime.now().isoformat()
        self.save_session()

    def get_messages_for_api(self) -> List[Dict[str, str]]:
        """Get messages in format suitable for API calls."""
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]

    def save_session(self) -> None:
        """Save the current session to a JSON file."""
        session_data = {
            "metadata": asdict(self.metadata),
            "messages": [asdict(msg) for msg in self.messages]
        }

        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

    def load_session(self) -> bool:
        """Load an existing session from JSON file. Returns True if successful."""
        if not self.session_file.exists():
            return False

        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            # Load metadata
            metadata_dict = session_data.get("metadata", {})
            self.metadata = SessionMetadata(**metadata_dict)

            # Load messages
            messages_data = session_data.get("messages", [])
            self.messages = [Message(**msg_dict) for msg_dict in messages_data]

            return True
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error loading session {self.session_id}: {e}")
            return False

    def get_session_summary(self) -> str:
        """Get a summary of the session."""
        if not self.messages:
            return f"Empty session with {self.model}"

        first_user_msg = next((msg.content for msg in self.messages if msg.role == "user"), "")
        preview = first_user_msg[:50] + "..." if len(first_user_msg) > 50 else first_user_msg

        return f"{self.session_id}: {preview} ({self.metadata.message_count} messages)"

    @classmethod
    def list_sessions(cls, sessions_dir: Optional[str] = None) -> List["ChatSession"]:
        """List all existing chat sessions."""
        sessions_path = Path(sessions_dir) if sessions_dir else Path.cwd() / "chat_sessions"
        if not sessions_path.exists():
            return []

        sessions = []
        for session_file in sessions_path.glob("*.json"):
            session_id = session_file.stem
            try:
                # Create session object and load it
                session = cls(model="", session_id=session_id, sessions_dir=str(sessions_path))
                if session.load_session():
                    sessions.append(session)
            except Exception as e:
                print(f"Error loading session {session_id}: {e}")

        # Sort by updated_at (most recent first)
        sessions.sort(key=lambda s: s.metadata.updated_at, reverse=True)
        return sessions

    def delete_session(self) -> bool:
        """Delete the session file."""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                return True
            return False
        except Exception as e:
            print(f"Error deleting session {self.session_id}: {e}")
            return False
