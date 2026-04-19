"""Service layer for conversation and message operations."""

import logging
import asyncio
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
        # De-duplicate while preserving caller-provided participant order.
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

        conversation.last_message_at = datetime.utcnow()
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
            unread_messages = []
            for message in messages:
                if user_id not in message.read_by_ids:
                    message.read_by_ids.append(user_id)
                    unread_messages.append(message)
                    changed = True
            if unread_messages:
                await asyncio.gather(*[message.save() for message in unread_messages])

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

    # ====================================================================
    # ROUTER-DELEGATED METHODS
    # ====================================================================

    async def get_current_user_profile(self, current_user: dict):
        """
        Resolve the caller into (profile_object, uid, role, sender_type).

        Checks Admin first, then Employee.

        Raises:
            HTTPException 404: User profile not found
        """
        from backend.models import Admin, Employee

        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if me:
            sender_type = "admin" if me.role in ["SuperAdmin", "Admin"] else "manager"
            return me, me.uid, me.role, sender_type

        uid = current_user.get("uid") or current_user.get("id")
        if uid:
            me = await Employee.find_one(Employee.uid == uid)
            if me:
                return me, me.uid, "Employee", "employee"

        self.raise_not_found("User profile not found")

    async def add_message_to_conversation_and_broadcast(
        self,
        conversation_id: int,
        sender_id: int,
        sender_name: str,
        sender_role: str,
        sender_type: str,
        content: str,
    ):
        """
        Insert a message, update conversation metadata, and broadcast via WebSocket.

        Returns:
            Created Message document
        """
        import json
        from backend.models import Conversation, Message
        from backend.websocket_manager import manager as ws_manager

        new_message = Message(
            uid=await self.get_next_uid("messages"),
            conversation_id=conversation_id,
            sender_id=sender_id,
            sender_name=sender_name,
            sender_role=sender_role,
            sender_type=sender_type,
            content=content,
            read_by_ids=[sender_id],
        )
        await new_message.insert()

        conv = await Conversation.find_one(Conversation.uid == conversation_id)
        if conv:
            conv.last_message_at = datetime.now()
            conv.last_message_preview = content[:50]
            for pid in conv.participant_ids:
                if pid != sender_id:
                    key = str(pid)
                    conv.unread_count_map[key] = conv.unread_count_map.get(key, 0) + 1
            await conv.save()

        await ws_manager.broadcast(
            json.dumps(
                {
                    "type": "new_message",
                    "conversation_id": conversation_id,
                    "participant_ids": conv.participant_ids if conv else [],
                    "message": {
                        "id": new_message.uid,
                        "sender_id": sender_id,
                        "sender_name": sender_name,
                        "content": content,
                        "timestamp": new_message.timestamp.isoformat(),
                    },
                }
            )
        )
        return new_message

    async def _create_conversation_record(
        self,
        conversation_type: str,
        created_by_id: int,
        created_by_name: str,
        created_by_role: str,
        participant_ids: list,
        participant_names: list,
        title: str,
    ):
        """Internal helper that delegates to the existing ``create_conversation``."""
        return await self.create_conversation(
            {
                "conversation_type": conversation_type,
                "created_by_id": created_by_id,
                "created_by_name": created_by_name,
                "created_by_role": created_by_role,
                "participant_ids": participant_ids,
                "participant_names": participant_names,
                "title": title,
            }
        )

    # --- broadcasts ---

    async def broadcast_to_all(self, content: str, current_user: dict) -> dict:
        """Admin broadcasts a message to everyone (all admins, managers, employees)."""
        from backend.models import Admin, Employee

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can create broadcasts")

        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me:
            self.raise_not_found("Admin profile not found")

        admins = await Admin.find(Admin.is_active == True).to_list()
        employees = await Employee.find(Employee.is_active == True).to_list()

        participant_ids = [a.uid for a in admins] + [e.uid for e in employees]
        participant_names = [a.full_name for a in admins] + [e.name for e in employees]

        conv = await self._create_conversation_record(
            conversation_type="broadcast_all",
            created_by_id=me.uid,
            created_by_name=me.full_name,
            created_by_role=me.role,
            participant_ids=participant_ids,
            participant_names=participant_names,
            title="📢 Broadcast: All",
        )

        await self.add_message_to_conversation_and_broadcast(
            conversation_id=conv.uid,
            sender_id=me.uid,
            sender_name=me.full_name,
            sender_role=me.role,
            sender_type="admin",
            content=content,
        )
        return {"message": "Broadcast sent to all users", "conversation_id": conv.uid}

    async def broadcast_to_managers(self, content: str, current_user: dict) -> dict:
        """Admin broadcasts a message to all Site Managers and Admins only."""
        from backend.models import Admin

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can create broadcasts")

        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me:
            self.raise_not_found("Admin profile not found")

        managers = await Admin.find(Admin.is_active == True).to_list()
        participant_ids = [a.uid for a in managers]
        participant_names = [a.full_name for a in managers]

        conv = await self._create_conversation_record(
            conversation_type="broadcast_managers",
            created_by_id=me.uid,
            created_by_name=me.full_name,
            created_by_role=me.role,
            participant_ids=participant_ids,
            participant_names=participant_names,
            title="📢 Broadcast: Managers",
        )

        await self.add_message_to_conversation_and_broadcast(
            conversation_id=conv.uid,
            sender_id=me.uid,
            sender_name=me.full_name,
            sender_role=me.role,
            sender_type="admin",
            content=content,
        )
        return {"message": "Broadcast sent to managers", "conversation_id": conv.uid}

    async def broadcast_to_employees(self, content: str, current_user: dict) -> dict:
        """Admin broadcasts a message to all Employees and Admins only."""
        from backend.models import Admin, Employee

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can create broadcasts")

        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me:
            self.raise_not_found("Admin profile not found")

        employees = await Employee.find(Employee.is_active == True).to_list()
        participant_ids = [me.uid] + [e.uid for e in employees]
        participant_names = [me.full_name] + [e.name for e in employees]

        conv = await self._create_conversation_record(
            conversation_type="broadcast_employees",
            created_by_id=me.uid,
            created_by_name=me.full_name,
            created_by_role=me.role,
            participant_ids=participant_ids,
            participant_names=participant_names,
            title="👨‍🔧 Broadcast: Employees Only",
        )

        await self.add_message_to_conversation_and_broadcast(
            conversation_id=conv.uid,
            sender_id=me.uid,
            sender_name=me.full_name,
            sender_role=me.role,
            sender_type="admin",
            content=content,
        )
        return {"message": "Broadcast sent to all employees", "conversation_id": conv.uid}

    async def broadcast_to_custom(
        self, content: str, recipient_ids: list, current_user: dict
    ) -> dict:
        """Admin broadcasts a message to a specific subset of users."""
        from backend.models import Admin, Employee

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can create broadcasts")

        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me:
            self.raise_not_found("Admin profile not found")

        if not recipient_ids:
            self.raise_bad_request("recipient_ids must not be empty")

        all_ids = list(set(recipient_ids) | {me.uid})

        admins = await Admin.find(Admin.is_active == True).to_list()
        employees = await Employee.find(Employee.is_active == True).to_list()

        uid_to_name: dict = {}
        for a in admins:
            uid_to_name[a.uid] = a.full_name
        for e in employees:
            uid_to_name[e.uid] = e.name

        participant_names = [uid_to_name.get(pid, f"User {pid}") for pid in all_ids]

        conv = await self._create_conversation_record(
            conversation_type="broadcast_custom",
            created_by_id=me.uid,
            created_by_name=me.full_name,
            created_by_role=me.role,
            participant_ids=all_ids,
            participant_names=participant_names,
            title="📢 Broadcast: Custom",
        )

        await self.add_message_to_conversation_and_broadcast(
            conversation_id=conv.uid,
            sender_id=me.uid,
            sender_name=me.full_name,
            sender_role=me.role,
            sender_type="admin",
            content=content,
        )
        return {"message": "Custom broadcast sent", "conversation_id": conv.uid}

    # --- private chat ---

    async def start_private_chat(
        self, recipient_id: int, content: str, current_user: dict
    ) -> dict:
        """Start (or reuse) a private one-on-one conversation."""
        from backend.models import Admin, Conversation, Employee

        me, my_id, my_role, my_type = await self.get_current_user_profile(current_user)

        recipient = await Admin.find_one(Admin.uid == recipient_id)
        if not recipient:
            recipient = await Employee.find_one(Employee.uid == recipient_id)
        if not recipient:
            self.raise_not_found("Recipient not found")

        recipient_name = getattr(recipient, "full_name", None) or getattr(recipient, "name", "Unknown")

        existing = await Conversation.find(
            Conversation.conversation_type == "private",
            Conversation.participant_ids == my_id,
            Conversation.participant_ids == recipient_id,
        ).first_or_none()

        if existing and len(existing.participant_ids) != 2:
            existing = None

        if existing:
            conv = existing
        else:
            my_name = getattr(me, "full_name", None) or getattr(me, "name", "Unknown")
            conv = await self._create_conversation_record(
                conversation_type="private",
                created_by_id=my_id,
                created_by_name=my_name,
                created_by_role=my_role,
                participant_ids=[my_id, recipient_id],
                participant_names=[my_name, recipient_name],
                title=f"💬 Chat: {my_name} & {recipient_name}",
            )

        await self.add_message_to_conversation_and_broadcast(
            conversation_id=conv.uid,
            sender_id=my_id,
            sender_name=getattr(me, "full_name", None) or getattr(me, "name", "Unknown"),
            sender_role=my_role,
            sender_type=my_type,
            content=content,
        )
        return {"message": "Private message sent", "conversation_id": conv.uid}

    # --- conversations & messages ---

    async def get_my_conversations(self, current_user: dict) -> list:
        """Get all conversations visible to the current user, sorted by most recent."""
        from backend.models import Conversation

        _, my_id, _, _ = await self.get_current_user_profile(current_user)

        conversations = (
            await Conversation.find(Conversation.participant_ids == my_id)
            .sort(-Conversation.last_message_at)
            .to_list()
        )

        result = []
        for conv in conversations:
            result.append(
                {
                    "id": conv.uid,
                    "type": conv.conversation_type,
                    "title": conv.title,
                    "last_message_at": conv.last_message_at.isoformat(),
                    "last_message_preview": conv.last_message_preview,
                    "unread_count": conv.unread_count_map.get(str(my_id), 0),
                    "participant_count": len(conv.participant_ids),
                    "created_by_name": conv.created_by_name,
                }
            )
        return result

    async def get_conversation_messages_for_user(
        self, conversation_id: int, current_user: dict
    ) -> list:
        """Get all messages in a conversation and mark them as read."""
        from backend.models import Conversation, Message

        conv = await Conversation.find_one(Conversation.uid == conversation_id)
        if not conv:
            self.raise_not_found("Conversation not found")

        _, my_id, _, _ = await self.get_current_user_profile(current_user)

        if my_id not in conv.participant_ids:
            self.raise_forbidden("You are not a participant in this conversation")

        messages = (
            await Message.find(Message.conversation_id == conversation_id)
            .sort(+Message.timestamp)
            .to_list()
        )

        unread_msgs = [msg for msg in messages if my_id not in msg.read_by_ids]
        for msg in unread_msgs:
            msg.read_by_ids.append(my_id)
        if unread_msgs:
            await asyncio.gather(*[msg.save() for msg in unread_msgs])

        conv.unread_count_map[str(my_id)] = 0
        await conv.save()

        return [
            {
                "id": msg.uid,
                "sender_id": msg.sender_id,
                "sender_name": msg.sender_name,
                "sender_role": msg.sender_role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "is_read": my_id in msg.read_by_ids,
            }
            for msg in messages
        ]

    async def reply_to_conversation(
        self, conversation_id: int, content: str, current_user: dict
    ) -> dict:
        """Reply to an existing conversation (broadcast or private)."""
        from backend.models import Conversation

        conv = await Conversation.find_one(Conversation.uid == conversation_id)
        if not conv:
            self.raise_not_found("Conversation not found")

        me, sender_id, sender_role, sender_type = await self.get_current_user_profile(
            current_user
        )
        sender_name = getattr(me, "full_name", None) or getattr(me, "name", "Unknown")

        if sender_id not in conv.participant_ids:
            self.raise_forbidden("You are not a participant in this conversation")

        await self.add_message_to_conversation_and_broadcast(
            conversation_id=conversation_id,
            sender_id=sender_id,
            sender_name=sender_name,
            sender_role=sender_role,
            sender_type=sender_type,
            content=content,
        )
        return {"message": "Reply sent"}

    # --- recipients ---

    async def get_available_recipients(self, current_user: dict) -> dict:
        """Get list of users who can receive messages. Only accessible by Admins."""
        from backend.models import Admin, Employee

        if current_user.get("role") not in ["SuperAdmin", "Admin"]:
            self.raise_forbidden("Only Admins can access recipient list")

        managers, employees, admins = await asyncio.gather(
            Admin.find(Admin.is_active == True, Admin.role == "Site Manager").to_list(),
            Employee.find(Employee.is_active == True).to_list(),
            Admin.find({"is_active": True, "role": {"$in": ["SuperAdmin", "Admin"]}}).to_list(),
        )

        return {
            "managers": [
                {"id": a.uid, "name": a.full_name, "role": a.role, "email": a.email}
                for a in managers
            ],
            "employees": [
                {"id": e.uid, "name": e.name, "designation": e.designation}
                for e in employees
            ],
            "admins": [
                {"id": a.uid, "name": a.full_name, "role": a.role, "email": a.email}
                for a in admins
            ],
        }

    async def get_manager_recipients(self, current_user: dict) -> dict:
        """
        Get list of users a manager can message.

        Only accessible by Site Managers.
        """
        from backend.models import Admin, DutyAssignment, Employee

        me = await Admin.find_one(Admin.email == current_user.get("sub"))
        if not me or me.role != "Site Manager":
            self.raise_forbidden("Only Site Managers can access this endpoint")

        admins = await Admin.find(
            {"is_active": True, "role": {"$in": ["SuperAdmin", "Admin"]}}
        ).to_list()

        assignments = await DutyAssignment.find(
            DutyAssignment.manager_id == me.uid
        ).to_list()
        employee_ids = [a.employee_id for a in assignments]

        employees = []
        if employee_ids:
            employees = await Employee.find(
                {"uid": {"$in": employee_ids}, "is_active": True}
            ).to_list()

        return {
            "admins": [
                {"id": a.uid, "name": a.full_name, "role": a.role, "email": a.email}
                for a in admins
            ],
            "employees": [
                {"id": e.uid, "name": e.name, "designation": e.designation}
                for e in employees
            ],
        }

    # --- unread ---

    async def get_total_unread_count(self, current_user: dict) -> dict:
        """Get total unread message count across all conversations."""
        from backend.models import Conversation

        _, my_id, _, _ = await self.get_current_user_profile(current_user)

        conversations = await Conversation.find(
            Conversation.participant_ids == my_id
        ).to_list()

        total_unread = sum(
            conv.unread_count_map.get(str(my_id), 0) for conv in conversations
        )
        return {"unread_count": total_unread}

    # --- private message with permissions ---

    async def send_private_message_with_permissions(
        self, recipient_id: int, content: str, current_user: dict
    ) -> dict:
        """
        Send a private message with full permission checks.

        Permission rules:
        - Admins can message anyone
        - Managers/Employees can message Admins
        - Managers CANNOT message other managers
        - Employees CANNOT message other employees
        - Manager↔Employee only when assigned via DutyAssignment
        """
        from backend.models import Admin, Conversation, DutyAssignment, Employee

        # 1. Sender info
        me_admin = await Admin.find_one(Admin.email == current_user.get("sub"))
        me_employee = None

        if me_admin:
            sender_id = me_admin.uid
            sender_name = me_admin.full_name
            sender_role = me_admin.role
            sender_type = "admin" if me_admin.role in ["SuperAdmin", "Admin"] else "manager"
        else:
            me_employee = await Employee.find_one(
                Employee.uid == current_user.get("uid")
            )
            if not me_employee:
                self.raise_not_found("User profile not found")
            sender_id = me_employee.uid
            sender_name = me_employee.name
            sender_role = "Employee"
            sender_type = "employee"

        # 2. Recipient info
        recipient_admin = await Admin.find_one(Admin.uid == recipient_id)
        recipient_employee = None

        if recipient_admin:
            recipient_name = recipient_admin.full_name
            recipient_type = (
                "admin" if recipient_admin.role in ["SuperAdmin", "Admin"] else "manager"
            )
        else:
            recipient_employee = await Employee.find_one(Employee.uid == recipient_id)
            if not recipient_employee:
                self.raise_not_found("Recipient not found")
            recipient_name = recipient_employee.name
            recipient_type = "employee"

        # 3. Permission checks
        if sender_id == recipient_id:
            self.raise_bad_request("Cannot send messages to yourself")

        if sender_type == "manager" and recipient_type == "manager":
            self.raise_forbidden(
                "Managers cannot send private messages to other managers"
            )

        if sender_type == "employee" and recipient_type == "employee":
            self.raise_forbidden(
                "Employees cannot send private messages to other employees"
            )

        if sender_type == "manager" and recipient_type == "employee":
            assignment = await DutyAssignment.find_one(
                DutyAssignment.employee_id == recipient_id,
                DutyAssignment.manager_id == sender_id,
            )
            if not assignment:
                self.raise_forbidden(
                    "Managers can only message employees assigned to them"
                )

        if sender_type == "employee" and recipient_type == "manager":
            assignment = await DutyAssignment.find_one(
                DutyAssignment.employee_id == sender_id,
                DutyAssignment.manager_id == recipient_id,
            )
            if not assignment:
                self.raise_forbidden(
                    "Employees can only message their assigned manager or admins"
                )

        # 4. Existing conversation check
        existing_conversations = await Conversation.find(
            Conversation.conversation_type == "private",
            Conversation.participant_ids == sender_id,
            Conversation.participant_ids == recipient_id,
        ).to_list()

        existing_conv = None
        for conv in existing_conversations:
            if len(conv.participant_ids) == 2:
                existing_conv = conv
                break

        # 5. Send message
        if existing_conv:
            await self.add_message_to_conversation_and_broadcast(
                conversation_id=existing_conv.uid,
                sender_id=sender_id,
                sender_name=sender_name,
                sender_role=sender_role,
                sender_type=sender_type,
                content=content,
            )
            return {
                "message": "Message sent",
                "conversation_id": existing_conv.uid,
                "is_new_conversation": False,
                "recipient_name": recipient_name,
            }

        title = f"💬 Chat with {recipient_name}"
        conv = await self._create_conversation_record(
            conversation_type="private",
            created_by_id=sender_id,
            created_by_name=sender_name,
            created_by_role=sender_role,
            participant_ids=[sender_id, recipient_id],
            participant_names=[sender_name, recipient_name],
            title=title,
        )

        await self.add_message_to_conversation_and_broadcast(
            conversation_id=conv.uid,
            sender_id=sender_id,
            sender_name=sender_name,
            sender_role=sender_role,
            sender_type=sender_type,
            content=content,
        )
        return {
            "message": "Private conversation started",
            "conversation_id": conv.uid,
            "is_new_conversation": True,
            "recipient_name": recipient_name,
        }
