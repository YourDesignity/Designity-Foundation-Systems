import asyncio
import logging
import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from backend.models import Conversation, Message, Admin, Employee, DutyAssignment
from backend.security import get_current_active_user
from backend.database import get_next_uid
from backend.websocket_manager import manager as ws_manager
from backend.utils.logger import setup_logger

router = APIRouter(
    prefix="/messages",
    tags=["Messages"],
    dependencies=[Depends(get_current_active_user)]
)

logger = setup_logger("MessagesRouter", log_file="logs/messages.log", level=logging.DEBUG)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def _get_current_user_profile(current_user: dict):
    """
    Returns (profile_object, uid, sender_role, sender_type).
    Checks Admin first, then Employee.
    """
    me = await Admin.find_one(Admin.email == current_user.get("sub"))
    if me:
        sender_type = "admin" if me.role in ["SuperAdmin", "Admin"] else "manager"
        return me, me.uid, me.role, sender_type

    uid = current_user.get("uid") or current_user.get("id")
    if uid:
        me = await Employee.find_one(Employee.uid == uid)
        if me:
            return me, me.uid, "Employee", "employee"

    raise HTTPException(status_code=404, detail="User profile not found")


async def create_conversation(
    conversation_type: str,
    created_by_id: int,
    created_by_name: str,
    created_by_role: str,
    participant_ids: List[int],
    participant_names: List[str],
    title: str,
) -> Conversation:
    """Helper to create a new conversation."""
    new_conv = Conversation(
        uid=await get_next_uid("conversations"),
        conversation_type=conversation_type,
        created_by_id=created_by_id,
        created_by_name=created_by_name,
        created_by_role=created_by_role,
        participant_ids=participant_ids,
        participant_names=participant_names,
        title=title,
        unread_count_map={str(pid): 0 for pid in participant_ids},
    )
    await new_conv.insert()
    logger.info(
        f"Created conversation: {title} (Type: {conversation_type}, Participants: {len(participant_ids)})"
    )
    return new_conv


async def add_message_to_conversation(
    conversation_id: int,
    sender_id: int,
    sender_name: str,
    sender_role: str,
    sender_type: str,
    content: str,
) -> Message:
    """Add a message to a conversation and update conversation metadata."""

    new_message = Message(
        uid=await get_next_uid("messages"),
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

    logger.info(f"Message added to conversation {conversation_id} by {sender_name}")

    # WebSocket broadcast with participant info for targeted notifications
    await ws_manager.broadcast(
        json.dumps(
            {
                "type": "new_message",
                "conversation_id": conversation_id,
                "participant_ids": conv.participant_ids if conv else [],  # Who should be notified
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


# =============================================================================
# ENDPOINT 1: BROADCAST TO ALL (PHASE 1)
# =============================================================================

@router.post("/broadcast/all", status_code=status.HTTP_201_CREATED)
async def broadcast_to_all(
    content: str,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Admin broadcasts a message to everyone (all admins, managers, employees).
    """
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create broadcasts")

    me = await Admin.find_one(Admin.email == current_user.get("sub"))
    if not me:
        raise HTTPException(status_code=404, detail="Admin profile not found")

    admins = await Admin.find(Admin.is_active == True).to_list()
    employees = await Employee.find(Employee.is_active == True).to_list()

    participant_ids = [a.uid for a in admins] + [e.uid for e in employees]
    participant_names = [a.full_name for a in admins] + [e.name for e in employees]

    conv = await create_conversation(
        conversation_type="broadcast_all",
        created_by_id=me.uid,
        created_by_name=me.full_name,
        created_by_role=me.role,
        participant_ids=participant_ids,
        participant_names=participant_names,
        title="📢 Broadcast: All",
    )

    await add_message_to_conversation(
        conversation_id=conv.uid,
        sender_id=me.uid,
        sender_name=me.full_name,
        sender_role=me.role,
        sender_type="admin",
        content=content,
    )

    return {"message": "Broadcast sent to all users", "conversation_id": conv.uid}


# =============================================================================
# ENDPOINT 2: BROADCAST TO MANAGERS ONLY
# =============================================================================

@router.post("/broadcast/managers", status_code=status.HTTP_201_CREATED)
async def broadcast_to_managers(
    content: str,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Admin broadcasts a message to all Site Managers and Admins only.
    """
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create broadcasts")

    me = await Admin.find_one(Admin.email == current_user.get("sub"))
    if not me:
        raise HTTPException(status_code=404, detail="Admin profile not found")

    managers = await Admin.find(Admin.is_active == True).to_list()

    participant_ids = [a.uid for a in managers]
    participant_names = [a.full_name for a in managers]

    conv = await create_conversation(
        conversation_type="broadcast_managers",
        created_by_id=me.uid,
        created_by_name=me.full_name,
        created_by_role=me.role,
        participant_ids=participant_ids,
        participant_names=participant_names,
        title="📢 Broadcast: Managers",
    )

    await add_message_to_conversation(
        conversation_id=conv.uid,
        sender_id=me.uid,
        sender_name=me.full_name,
        sender_role=me.role,
        sender_type="admin",
        content=content,
    )

    return {"message": "Broadcast sent to managers", "conversation_id": conv.uid}


# =============================================================================
# ENDPOINT 3: BROADCAST TO EMPLOYEES ONLY
# =============================================================================

@router.post("/broadcast/employees", status_code=status.HTTP_201_CREATED)
async def broadcast_to_employees(
    content: str,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Admin broadcasts a message to all Employees and Admins only.
    """
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create broadcasts")

    me = await Admin.find_one(Admin.email == current_user.get("sub"))
    if not me:
        raise HTTPException(status_code=404, detail="Admin profile not found")

    employees = await Employee.find(Employee.is_active == True).to_list()

    # Include admin in conversation so they can see replies
    participant_ids = [me.uid] + [e.uid for e in employees]
    participant_names = [me.full_name] + [e.name for e in employees]

    conv = await create_conversation(
        conversation_type="broadcast_employees",
        created_by_id=me.uid,
        created_by_name=me.full_name,
        created_by_role=me.role,
        participant_ids=participant_ids,
        participant_names=participant_names,
        title="👨‍🔧 Broadcast: Employees Only",
    )

    await add_message_to_conversation(
        conversation_id=conv.uid,
        sender_id=me.uid,
        sender_name=me.full_name,
        sender_role=me.role,
        sender_type="admin",
        content=content,
    )

    return {"message": "Broadcast sent to all employees", "conversation_id": conv.uid}


# =============================================================================
# ENDPOINT 4: BROADCAST TO CUSTOM RECIPIENTS
# =============================================================================


class CustomBroadcastRequest(BaseModel):
    content: str
    recipient_ids: List[int]  # UIDs of selected admins/employees


@router.post("/broadcast/custom", status_code=status.HTTP_201_CREATED)
async def broadcast_to_custom(
    payload: CustomBroadcastRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Admin broadcasts a message to a specific subset of users.
    """
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can create broadcasts")

    me = await Admin.find_one(Admin.email == current_user.get("sub"))
    if not me:
        raise HTTPException(status_code=404, detail="Admin profile not found")

    if not payload.recipient_ids:
        raise HTTPException(status_code=400, detail="recipient_ids must not be empty")

    # Ensure sender is always included
    all_ids = list(set(payload.recipient_ids) | {me.uid})

    # Resolve names for all recipients
    admins = await Admin.find(Admin.is_active == True).to_list()
    employees = await Employee.find(Employee.is_active == True).to_list()

    uid_to_name: dict = {}
    for a in admins:
        uid_to_name[a.uid] = a.full_name
    for e in employees:
        uid_to_name[e.uid] = e.name

    participant_names = [uid_to_name.get(pid, f"User {pid}") for pid in all_ids]

    conv = await create_conversation(
        conversation_type="broadcast_custom",
        created_by_id=me.uid,
        created_by_name=me.full_name,
        created_by_role=me.role,
        participant_ids=all_ids,
        participant_names=participant_names,
        title="📢 Broadcast: Custom",
    )

    await add_message_to_conversation(
        conversation_id=conv.uid,
        sender_id=me.uid,
        sender_name=me.full_name,
        sender_role=me.role,
        sender_type="admin",
        content=payload.content,
    )

    return {"message": "Custom broadcast sent", "conversation_id": conv.uid}


# =============================================================================
# ENDPOINT 5: START PRIVATE CHAT (Admin ↔ Manager)
# =============================================================================

class PrivateChatRequest(BaseModel):
    recipient_id: int
    content: str


@router.post("/private", status_code=status.HTTP_201_CREATED)
async def start_private_chat(
    payload: PrivateChatRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Start (or reuse) a private one-on-one conversation between the current user
    and another user. Each pair shares at most one private conversation.
    """
    me, my_id, my_role, my_type = await _get_current_user_profile(current_user)

    # Look up recipient
    recipient = await Admin.find_one(Admin.uid == payload.recipient_id)
    if not recipient:
        recipient = await Employee.find_one(Employee.uid == payload.recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    recipient_name = getattr(recipient, "full_name", None) or getattr(recipient, "name", "Unknown")

    # Check if a private conversation already exists between these two users
    # (exactly two participants - not a group conversation)
    existing = await Conversation.find(
        Conversation.conversation_type == "private",
        Conversation.participant_ids == my_id,
        Conversation.participant_ids == payload.recipient_id,
    ).first_or_none()

    # Verify it really is a 1-on-1 thread (no extra participants)
    if existing and len(existing.participant_ids) != 2:
        existing = None

    if existing:
        conv = existing
    else:
        my_name = getattr(me, "full_name", None) or getattr(me, "name", "Unknown")
        conv = await create_conversation(
            conversation_type="private",
            created_by_id=my_id,
            created_by_name=my_name,
            created_by_role=my_role,
            participant_ids=[my_id, payload.recipient_id],
            participant_names=[my_name, recipient_name],
            title=f"💬 Chat: {my_name} & {recipient_name}",
        )

    await add_message_to_conversation(
        conversation_id=conv.uid,
        sender_id=my_id,
        sender_name=getattr(me, "full_name", None) or getattr(me, "name", "Unknown"),
        sender_role=my_role,
        sender_type=my_type,
        content=payload.content,
    )

    return {"message": "Private message sent", "conversation_id": conv.uid}


# =============================================================================
# ENDPOINT 6: GET MY CONVERSATIONS
# =============================================================================

@router.get("/conversations")
async def get_my_conversations(current_user: dict = Depends(get_current_active_user)):
    """Get all conversations visible to the current user, sorted by most recent."""
    _, my_id, _, _ = await _get_current_user_profile(current_user)

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


# =============================================================================
# ENDPOINT 7: GET MESSAGES IN A CONVERSATION
# =============================================================================

@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Get all messages in a conversation and mark them as read."""
    conv = await Conversation.find_one(Conversation.uid == conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    _, my_id, _, _ = await _get_current_user_profile(current_user)

    if my_id not in conv.participant_ids:
        raise HTTPException(
            status_code=403, detail="You are not a participant in this conversation"
        )

    messages = (
        await Message.find(Message.conversation_id == conversation_id)
        .sort(+Message.timestamp)
        .to_list()
    )

    # Batch-mark unread messages as read in parallel to avoid N+1 saves
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


# =============================================================================
# ENDPOINT 8: REPLY TO A CONVERSATION
# =============================================================================

@router.post("/{conversation_id}/reply", status_code=status.HTTP_201_CREATED)
async def reply_to_conversation(
    conversation_id: int,
    content: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Reply to an existing conversation (broadcast or private)."""
    conv = await Conversation.find_one(Conversation.uid == conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    me, sender_id, sender_role, sender_type = await _get_current_user_profile(current_user)
    sender_name = getattr(me, "full_name", None) or getattr(me, "name", "Unknown")

    if sender_id not in conv.participant_ids:
        raise HTTPException(
            status_code=403, detail="You are not a participant in this conversation"
        )

    await add_message_to_conversation(
        conversation_id=conversation_id,
        sender_id=sender_id,
        sender_name=sender_name,
        sender_role=sender_role,
        sender_type=sender_type,
        content=content,
    )

    return {"message": "Reply sent"}


# =============================================================================
# ENDPOINT 9: GET AVAILABLE RECIPIENTS (PHASE 2)
# =============================================================================

@router.get("/recipients")
async def get_available_recipients(current_user: dict = Depends(get_current_active_user)):
    """
    Get list of users who can receive messages.

    Used by frontend to populate recipient selection UI.
    Only accessible by Admins.
    """
    if current_user.get("role") not in ["SuperAdmin", "Admin"]:
        raise HTTPException(status_code=403, detail="Only Admins can access recipient list")

    managers, employees, admins = await asyncio.gather(
        Admin.find(Admin.is_active == True, Admin.role == "Site Manager").to_list(),
        Employee.find(Employee.is_active == True).to_list(),
        Admin.find({"is_active": True, "role": {"$in": ["SuperAdmin", "Admin"]}}).to_list(),
    )

    result = {
        "managers": [
            {
                "id": a.uid,
                "name": a.full_name,
                "role": a.role,
                "email": a.email,
            }
            for a in managers
        ],
        "employees": [
            {
                "id": e.uid,
                "name": e.name,
                "designation": e.designation,
            }
            for e in employees
        ],
        "admins": [
            {
                "id": a.uid,
                "name": a.full_name,
                "role": a.role,
                "email": a.email,
            }
            for a in admins
        ],
    }

    logger.info(f"Recipient list requested by {current_user.get('sub')}")

    return result


# =============================================================================
# ENDPOINT: GET MANAGER RECIPIENTS
# =============================================================================

@router.get("/manager-recipients")
async def get_manager_recipients(current_user: dict = Depends(get_current_active_user)):
    """
    Get list of users a manager can message:
    - All Admins (SuperAdmin and Admin roles)
    - Employees assigned to this manager (via DutyAssignment)

    Only accessible by Site Managers.
    """
    me = await Admin.find_one(Admin.email == current_user.get("sub"))
    if not me or me.role != "Site Manager":
        raise HTTPException(status_code=403, detail="Only Site Managers can access this endpoint")

    # Get all admins
    admins = await Admin.find(
        {
            "is_active": True,
            "role": {"$in": ["SuperAdmin", "Admin"]}
        }
    ).to_list()

    # Get employees assigned to this manager via DutyAssignment
    assignments = await DutyAssignment.find(
        DutyAssignment.manager_id == me.uid
    ).to_list()

    employee_ids = [a.employee_id for a in assignments]

    employees = []
    if employee_ids:
        employees = await Employee.find(
            {
                "uid": {"$in": employee_ids},
                "is_active": True
            }
        ).to_list()

    result = {
        "admins": [
            {
                "id": a.uid,
                "name": a.full_name,
                "role": a.role,
                "email": a.email,
            }
            for a in admins
        ],
        "employees": [
            {
                "id": e.uid,
                "name": e.name,
                "designation": e.designation,
            }
            for e in employees
        ],
    }

    logger.info(f"Manager {me.full_name} requested recipient list")

    return result


# =============================================================================
# ENDPOINT: GET TOTAL UNREAD MESSAGE COUNT
# =============================================================================

@router.get("/unread-count")
async def get_total_unread_count(current_user: dict = Depends(get_current_active_user)):
    """
    Get total unread message count across all conversations for the current user.

    Used for notification badge in header.
    Returns: {"unread_count": <number>}
    """
    _, my_id, _, _ = await _get_current_user_profile(current_user)

    # Get all conversations where user is a participant
    conversations = await Conversation.find(
        Conversation.participant_ids == my_id
    ).to_list()

    # Sum up all unread counts from all conversations
    total_unread = sum(
        conv.unread_count_map.get(str(my_id), 0)
        for conv in conversations
    )

    logger.debug(f"User {my_id} has {total_unread} total unread messages across {len(conversations)} conversations")

    return {"unread_count": total_unread}


# =============================================================================
# ENDPOINT: SEND PRIVATE MESSAGE (PHASE 3)
# =============================================================================

@router.post("/private/{recipient_id}", status_code=status.HTTP_201_CREATED)
async def send_private_message(
    recipient_id: int,
    content: str,
    current_user: dict = Depends(get_current_active_user)
):
    """
    Send a private message to a specific user (or start a private conversation).

    - Admins can message anyone
    - Managers/Employees can message Admins
    - Managers CANNOT message other managers
    - Employees CANNOT message other employees

    If a conversation already exists between these two users, the message is added to it.
    Otherwise, a new private conversation is created.

    Phase 3 Implementation.
    """

    # =========================================================================
    # 1. GET SENDER INFO
    # =========================================================================

    me_admin = await Admin.find_one(Admin.email == current_user.get("sub"))
    me_employee = None

    if me_admin:
        sender_id = me_admin.uid
        sender_name = me_admin.full_name
        sender_role = me_admin.role
        sender_type = "admin" if me_admin.role in ["SuperAdmin", "Admin"] else "manager"
    else:
        # Check if sender is employee
        me_employee = await Employee.find_one(Employee.uid == current_user.get("uid"))
        if not me_employee:
            raise HTTPException(404, "User profile not found")
        sender_id = me_employee.uid
        sender_name = me_employee.name
        sender_role = "Employee"
        sender_type = "employee"

    # =========================================================================
    # 2. GET RECIPIENT INFO
    # =========================================================================

    recipient_admin = await Admin.find_one(Admin.uid == recipient_id)
    recipient_employee = None

    if recipient_admin:
        recipient_name = recipient_admin.full_name
        recipient_role = recipient_admin.role
        recipient_type = "admin" if recipient_admin.role in ["SuperAdmin", "Admin"] else "manager"
    else:
        recipient_employee = await Employee.find_one(Employee.uid == recipient_id)
        if not recipient_employee:
            raise HTTPException(404, "Recipient not found")
        recipient_name = recipient_employee.name
        recipient_role = "Employee"
        recipient_type = "employee"

    # =========================================================================
    # 3. PERMISSION CHECKS (CRITICAL SECURITY)
    # =========================================================================

    # Rule 1: Cannot message yourself
    if sender_id == recipient_id:
        raise HTTPException(400, "Cannot send messages to yourself")

    # Rule 2: Managers cannot message other managers
    if sender_type == "manager" and recipient_type == "manager":
        raise HTTPException(403, "Managers cannot send private messages to other managers")

    # Rule 3: Employees cannot message other employees
    if sender_type == "employee" and recipient_type == "employee":
        raise HTTPException(403, "Employees cannot send private messages to other employees")

    # Rule 4: Managers can message admins OR their assigned employees
    if sender_type == "manager" and recipient_type == "employee":
        # Check if employee is assigned to this manager
        assignment = await DutyAssignment.find_one(
            DutyAssignment.employee_id == recipient_id,
            DutyAssignment.manager_id == sender_id
        )

        if not assignment:
            raise HTTPException(
                403,
                "Managers can only message employees assigned to them"
            )

    # Rule 5: Employees can only message admins or their assigned manager
    if sender_type == "employee" and recipient_type == "manager":
        # Check if this manager is assigned to this employee
        assignment = await DutyAssignment.find_one(
            DutyAssignment.employee_id == sender_id,
            DutyAssignment.manager_id == recipient_id
        )

        if not assignment:
            raise HTTPException(
                403,
                "Employees can only message their assigned manager or admins"
            )

    # =========================================================================
    # 4. CHECK IF CONVERSATION ALREADY EXISTS (BIDIRECTIONAL)
    # =========================================================================

    # Search for existing private conversation between these two users
    # Filter by both participant IDs in the DB query, then verify exact 1-on-1 size
    existing_conversations = await Conversation.find(
        Conversation.conversation_type == "private",
        Conversation.participant_ids == sender_id,
        Conversation.participant_ids == recipient_id,
    ).to_list()

    existing_conv = None
    for conv in existing_conversations:
        # Confirm it is a strict 1-on-1 thread (no extra participants)
        if len(conv.participant_ids) == 2:
            existing_conv = conv
            break

    # =========================================================================
    # 5. ADD MESSAGE TO EXISTING CONVERSATION OR CREATE NEW ONE
    # =========================================================================

    if existing_conv:
        # Add message to existing conversation
        await add_message_to_conversation(
            conversation_id=existing_conv.uid,
            sender_id=sender_id,
            sender_name=sender_name,
            sender_role=sender_role,
            sender_type=sender_type,
            content=content
        )

        logger.info(f"Private message added to existing conversation {existing_conv.uid} by {sender_name}")

        return {
            "message": "Message sent",
            "conversation_id": existing_conv.uid,
            "is_new_conversation": False,
            "recipient_name": recipient_name
        }

    # Create new private conversation
    # Title ALWAYS shows the recipient's name (the person you're chatting with)
    title = f"💬 Chat with {recipient_name}"

    conv = await create_conversation(
        conversation_type="private",
        created_by_id=sender_id,
        created_by_name=sender_name,
        created_by_role=sender_role,
        participant_ids=[sender_id, recipient_id],
        participant_names=[sender_name, recipient_name],
        title=title
    )

    await add_message_to_conversation(
        conversation_id=conv.uid,
        sender_id=sender_id,
        sender_name=sender_name,
        sender_role=sender_role,
        sender_type=sender_type,
        content=content
    )

    logger.info(f"New private conversation {conv.uid} created: {sender_name} → {recipient_name}")

    return {
        "message": "Private conversation started",
        "conversation_id": conv.uid,
        "is_new_conversation": True,
        "recipient_name": recipient_name
    }
