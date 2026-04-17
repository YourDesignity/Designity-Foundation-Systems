"""Service layer for conversation and message operations."""

from typing import Any

from backend.database import get_next_uid
from backend.services.base_service import BaseService


class MessagingService(BaseService):
    """Conversation and message CRUD operations."""

    async def create_conversation(self, payload: Any):
        from backend.models import Conversation

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("conversations")
        conversation = Conversation(**data)
        await conversation.insert()
        return conversation

    async def get_conversation_by_id(self, conversation_id: int):
        from backend.models import Conversation

        conversation = await Conversation.find_one(Conversation.uid == conversation_id)
        if not conversation:
            self.raise_not_found(f"Conversation {conversation_id} not found")
        return conversation

    async def create_message(self, payload: Any):
        from backend.models import Message

        data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)
        data["uid"] = await get_next_uid("messages")
        message = Message(**data)
        await message.insert()
        return message

    async def get_messages_for_conversation(self, conversation_id: int):
        from backend.models import Message

        return await Message.find(Message.conversation_id == conversation_id).sort("+created_at").to_list()
