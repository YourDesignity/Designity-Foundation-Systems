"""Messaging system models."""

from datetime import datetime
from typing import Dict, List, Optional

from beanie import Document
from pydantic import Field

from backend.models.base import MemoryNode


class Conversation(Document, MemoryNode):
    """
    Represents a message thread (broadcast or private chat).

    Types:
    - broadcast_all: Everyone can see
    - broadcast_managers: Only managers + admins (Phase 2)
    - broadcast_employees: Only employees + admins (Phase 2)
    - broadcast_custom: Selected recipients only (Phase 2)
    - private: One-on-one chat (Phase 3)
    """

    conversation_type: str  # "broadcast_all", "broadcast_managers", "broadcast_employees", "broadcast_custom", "private"
    created_by_id: int  # Admin.uid who created conversation
    created_by_name: str  # For display purposes
    created_by_role: str  # "SuperAdmin", "Admin", "Site Manager", "Employee"

    participant_ids: List[int] = []  # UIDs of people who can see this thread
    participant_names: List[str] = []  # For display (denormalized for performance)

    title: str  # "Broadcast: All", "Chat with Manager John", etc.
    last_message_at: datetime = Field(default_factory=datetime.now)
    last_message_preview: Optional[str] = None  # First 50 chars of last message

    unread_count_map: Dict[str, int] = {}  # {str(user_id): unread_count}

    class Settings:
        name = "conversations"
        indexes = [
            [("created_by_id", 1)],
            [("last_message_at", -1)],
        ]


class Message(Document, MemoryNode):
    """
    Individual message within a conversation thread.
    """

    conversation_id: int  # Links to Conversation.uid

    sender_id: int  # Who sent it (Admin.uid / Employee.uid)
    sender_name: str  # Display name
    sender_role: str  # "SuperAdmin", "Admin", "Site Manager", "Employee"
    sender_type: str  # "admin", "manager", "employee" (lowercase for filtering)

    content: str  # Message text
    timestamp: datetime = Field(default_factory=datetime.now)

    read_by_ids: List[int] = []  # UIDs of users who have read this message

    class Settings:
        name = "messages"
        indexes = [
            [("conversation_id", 1), ("timestamp", -1)],
            [("sender_id", 1)],
        ]
