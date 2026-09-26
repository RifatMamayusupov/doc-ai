"""
Monister Sessions - Chat session management with persistence.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

from config import settings


class ChatMessage(BaseModel):
    """A single chat message."""
    id: str
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str


class ChatSession(BaseModel):
    """A chat session with messages."""
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: list[ChatMessage] = []


class SessionManager:
    """Manage chat sessions with JSON file persistence."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or (settings.base_dir / "sessions")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.sessions_file = self.storage_path / "sessions.json"
        self._sessions: dict[str, ChatSession] = {}
        self._load_sessions()
    
    def _load_sessions(self):
        """Load sessions from JSON file."""
        if self.sessions_file.exists():
            try:
                data = json.loads(self.sessions_file.read_text(encoding="utf-8"))
                for session_data in data.get("sessions", []):
                    session = ChatSession(**session_data)
                    self._sessions[session.id] = session
            except Exception as e:
                print(f"Error loading sessions: {e}")
                self._sessions = {}
    
    def _save_sessions(self):
        """Save sessions to JSON file."""
        try:
            data = {
                "sessions": [s.model_dump() for s in self._sessions.values()]
            }
            self.sessions_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"Error saving sessions: {e}")
    
    def create_session(self, title: str = "Yangi chat") -> ChatSession:
        """Create a new chat session."""
        now = datetime.now().isoformat()
        session = ChatSession(
            id=f"session-{int(datetime.now().timestamp() * 1000)}",
            title=title,
            created_at=now,
            updated_at=now,
            messages=[]
        )
        self._sessions[session.id] = session
        self._save_sessions()
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)
    
    def get_all_sessions(self) -> list[ChatSession]:
        """Get all sessions, sorted by updated_at descending."""
        return sorted(
            self._sessions.values(),
            key=lambda s: s.updated_at,
            reverse=True
        )
    
    def update_session_title(self, session_id: str, title: str) -> Optional[ChatSession]:
        """Update session title."""
        session = self._sessions.get(session_id)
        if session:
            session.title = title
            session.updated_at = datetime.now().isoformat()
            self._save_sessions()
        return session
    
    def add_message(self, session_id: str, message: ChatMessage) -> Optional[ChatSession]:
        """Add a message to a session."""
        session = self._sessions.get(session_id)
        if session:
            session.messages.append(message)
            session.updated_at = datetime.now().isoformat()
            
            # Auto-update title from first user message
            if len(session.messages) == 1 and message.role == "user":
                title = message.content[:50]
                if len(message.content) > 50:
                    title += "..."
                session.title = title
            
            self._save_sessions()
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            self._save_sessions()
            return True
        return False
    
    def clear_session_messages(self, session_id: str) -> Optional[ChatSession]:
        """Clear all messages from a session."""
        session = self._sessions.get(session_id)
        if session:
            session.messages = []
            session.updated_at = datetime.now().isoformat()
            self._save_sessions()
        return session


# Global session manager instance
session_manager = SessionManager()


# Export
__all__ = [
    "ChatMessage",
    "ChatSession", 
    "SessionManager",
    "session_manager",
]
