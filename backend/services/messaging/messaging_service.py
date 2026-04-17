"""Service layer for conversation and message operations."""

import logging
from datetime import datetime
from typing import Any

from backend.services.base_service import BaseService

logger = logging.getLogger("MainApp")


class MessagingService(BaseService):
    """Conversation and message business operations."""

    # ====================================================================
    # HELPERS
    # ====================================================================

    @staticmethod
    def _to_dict(payload: Any) -> dict:
        return payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

    # ====================================================================
    # CONVERSATIONS
    # ====================================================================

    async def create_conversation(self, payload: Any):
        """
        Create a new conversation thread.

        Validations:
        - participant_ids must not be empty
        - title must not be empty

        Args:
            payload: Conversation payload

        Returns:
            Created Conversation document

        Raises:
            HTTPException 400: Validation errors
        """
        from backend.models import Conversation

        data = self._to_dict(payload)
        participant_ids = list(dict.fromkeys(data.get("participant_ids") or []))
        title = str(data.get("title") or "").strip()

        if not participant_ids:
            self.raise_bad_request("participant_ids must not be empty")
        if not title:
            self.raise_bad_request("title is required")

        uid = await self.get_next_uid("conversations")
        conversation = Conversation(
            uid=uid,
            conversation_type=data.get("conversation_type") or "private",
            created_by_id=int(data.get("created_by_id", 0) or 0),
            created_by_name=data.get("created_by_name") or "System",
            created_by_role=data.get("created_by_role") or "System",
            participant_ids=participant_ids,
            participant_names=data.get("participant_names") or [f"User {pid}" for pid in participant_ids],
            title=title,
            unread_count_map={str(pid): 0 for pid in participant_ids},
        )
        await conversation.insert()
        logger.info("Conversation created: %s (ID: %s)", conversation.title, conversation.uid)
        return conversation

    async def get_conversation_by_id(self, conversation_id: int):
        """
        Retrieve one conversation by UID.

        Raises:
            HTTPException 404: Conversation not found
        """
        from backend.models import Conversation

        conversation = await Conversation.find_one(Conversation.uid == conversation_id)
        if not conversation:
            self.raise_not_found("Conversation not found")
        return conversation

    async def get_user_conversations(self, user_id: int) -> list:
        """
        Retrieve all conversations for a user.

        Args:
            user_id: Participant UID

        Returns:
            Conversations sorted by latest message
        """
        from backend.models import Conversation

        return await Conversation.find(Conversation.participant_ids == user_id).sort(-Conversation.last_message_at).to_list()

    # ====================================================================
    # MESSAGES
    # ====================================================================

    async def send_message(
        self,
        conversation_id: int,
        sender_id: int,
        sender_name: str,
        sender_role: str,
        sender_type: str,
        content: str,
    ):
        """
        Send a message to an existing conversation.

        Validations:
        - Conversation must exist
        - Sender must be a participant
        - content must not be empty

        Returns:
            Created Message document

        Raises:
            HTTPException 400: Validation errors
            HTTPException 403: Sender is not a participant
            HTTPException 404: Conversation not found
        """
        from backend.models import Message

        body = (content or "").strip()
        if not body:
            self.raise_bad_request("content is required")

        conversation = await self.get_conversation_by_id(conversation_id)
        if sender_id not in conversation.participant_ids:
            self.raise_forbidden("Sender is not a participant in this conversation")

        message = Message(
            uid=await self.get_next_uid("messages"),
            conversation_id=conversation_id,
            sender_id=sender_id,
            sender_name=sender_name,
            sender_role=sender_role,
            sender_type=sender_type,
            content=body,
            read_by_ids=[sender_id],
        )
        await message.insert()

        conversation.last_message_at = datetime.now()
        conversation.last_message_preview = body[:50]
        for participant_id in conversation.participant_ids:
            if participant_id != sender_id:
                key = str(participant_id)
                conversation.unread_count_map[key] = conversation.unread_count_map.get(key, 0) + 1
        await conversation.save()

        logger.info("Message sent in conversation %s by user %s", conversation_id, sender_id)
        return message

    async def get_conversation_messages(self, conversation_id: int, user_id: int | None = None) -> list:
        """
        Retrieve conversation message history.

        Validations:
        - Conversation must exist
        - If user_id provided, user must be a participant

        Args:
            conversation_id: Conversation UID
            user_id: Optional viewer UID for access/read-state updates

        Returns:
            Messages sorted chronologically
        """
        from backend.models import Message

        conversation = await self.get_conversation_by_id(conversation_id)
        if user_id is not None and user_id not in conversation.participant_ids:
            self.raise_forbidden("You are not a participant in this conversation")

        messages = await Message.find(Message.conversation_id == conversation_id).sort(+Message.timestamp).to_list()

        if user_id is not None:
            changed = False
            for message in messages:
                if user_id not in message.read_by_ids:
                    message.read_by_ids.append(user_id)
                    await message.save()
                    changed = True

            if changed:
                conversation.unread_count_map[str(user_id)] = 0
                await conversation.save()

        return messages

    async def mark_message_read(self, message_id: int, user_id: int):
        """
        Mark a message as read by one user.

        Validations:
        - Message must exist
        - User must be a participant in the message conversation

        Returns:
            Updated Message document
        """
        from backend.models import Message

        message = await Message.find_one(Message.uid == message_id)
        if not message:
            self.raise_not_found("Message not found")

        conversation = await self.get_conversation_by_id(message.conversation_id)
        if user_id not in conversation.participant_ids:
            self.raise_forbidden("You are not a participant in this conversation")

        if user_id not in message.read_by_ids:
            message.read_by_ids.append(user_id)
            await message.save()

        conversation.unread_count_map[str(user_id)] = max(0, conversation.unread_count_map.get(str(user_id), 0) - 1)
        await conversation.save()

        logger.info("Message %s marked as read by user %s", message_id, user_id)
        return message

    async def delete_message(self, message_id: int, requester_id: int) -> bool:
        """
        Delete a message.

        Validations:
        - Message must exist
        - Requester must be sender or conversation owner

        Returns:
            True when deleted

        Raises:
            HTTPException 403: Not authorized
            HTTPException 404: Message not found
        """
        from backend.models import Message

        message = await Message.find_one(Message.uid == message_id)
        if not message:
            self.raise_not_found("Message not found")

        conversation = await self.get_conversation_by_id(message.conversation_id)
        if requester_id not in {message.sender_id, conversation.created_by_id}:
            self.raise_forbidden("You are not allowed to delete this message")

        await message.delete()

        latest = await Message.find(Message.conversation_id == conversation.uid).sort(-Message.timestamp).first_or_none()
        if latest:
            conversation.last_message_at = latest.timestamp
            conversation.last_message_preview = latest.content[:50]
        else:
            conversation.last_message_preview = None
        await conversation.save()

        logger.warning("Message deleted: %s by user %s", message_id, requester_id)
        return True

    # ====================================================================
    # BACKWARD-COMPAT HELPERS
    # ====================================================================

    async def create_message(self, payload: Any):
        """Backward-compatible message create wrapper."""
        data = self._to_dict(payload)
        return await self.send_message(
            conversation_id=int(data.get("conversation_id")),
            sender_id=int(data.get("sender_id")),
            sender_name=data.get("sender_name") or "Unknown",
            sender_role=data.get("sender_role") or "Unknown",
            sender_type=data.get("sender_type") or "unknown",
            content=data.get("content") or "",
        )

    async def get_messages_for_conversation(self, conversation_id: int):
        """Backward-compatible message history wrapper."""
        return await self.get_conversation_messages(conversation_id)
