from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from typing import List
from backend.security import get_current_active_user

router = APIRouter(
    prefix="/messages",
    tags=["Messages"],
    dependencies=[Depends(get_current_active_user)]
)


class CustomBroadcastRequest(BaseModel):
    content: str
    recipient_ids: List[int]


class PrivateChatRequest(BaseModel):
    recipient_id: int
    content: str


def _get_service():
    from backend.services.messaging.messaging_service import MessagingService
    return MessagingService()


# =============================================================================
# BROADCAST ENDPOINTS
# =============================================================================

@router.post("/broadcast/all", status_code=status.HTTP_201_CREATED)
async def broadcast_to_all(
    content: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Admin broadcasts a message to everyone (all admins, managers, employees)."""
    return await _get_service().broadcast_to_all(content, current_user)


@router.post("/broadcast/managers", status_code=status.HTTP_201_CREATED)
async def broadcast_to_managers(
    content: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Admin broadcasts a message to all Site Managers and Admins only."""
    return await _get_service().broadcast_to_managers(content, current_user)


@router.post("/broadcast/employees", status_code=status.HTTP_201_CREATED)
async def broadcast_to_employees(
    content: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Admin broadcasts a message to all Employees and Admins only."""
    return await _get_service().broadcast_to_employees(content, current_user)


@router.post("/broadcast/custom", status_code=status.HTTP_201_CREATED)
async def broadcast_to_custom(
    payload: CustomBroadcastRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """Admin broadcasts a message to a specific subset of users."""
    return await _get_service().broadcast_to_custom(
        payload.content, payload.recipient_ids, current_user
    )


# =============================================================================
# PRIVATE CHAT ENDPOINTS
# =============================================================================

@router.post("/private", status_code=status.HTTP_201_CREATED)
async def start_private_chat(
    payload: PrivateChatRequest,
    current_user: dict = Depends(get_current_active_user),
):
    """
    Start (or reuse) a private one-on-one conversation between the current user
    and another user. Each pair shares at most one private conversation.
    """
    return await _get_service().start_private_chat(
        payload.recipient_id, payload.content, current_user
    )


@router.post("/private/{recipient_id}", status_code=status.HTTP_201_CREATED)
async def send_private_message(
    recipient_id: int,
    content: str,
    current_user: dict = Depends(get_current_active_user),
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
    return await _get_service().send_private_message_with_permissions(
        recipient_id, content, current_user
    )


# =============================================================================
# CONVERSATION & MESSAGE ENDPOINTS
# =============================================================================

@router.get("/conversations")
async def get_my_conversations(current_user: dict = Depends(get_current_active_user)):
    """Get all conversations visible to the current user, sorted by most recent."""
    return await _get_service().get_my_conversations(current_user)


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    current_user: dict = Depends(get_current_active_user),
):
    """Get all messages in a conversation and mark them as read."""
    return await _get_service().get_conversation_messages_for_user(
        conversation_id, current_user
    )


@router.post("/{conversation_id}/reply", status_code=status.HTTP_201_CREATED)
async def reply_to_conversation(
    conversation_id: int,
    content: str,
    current_user: dict = Depends(get_current_active_user),
):
    """Reply to an existing conversation (broadcast or private)."""
    return await _get_service().reply_to_conversation(
        conversation_id, content, current_user
    )


# =============================================================================
# RECIPIENT ENDPOINTS
# =============================================================================

@router.get("/recipients")
async def get_available_recipients(current_user: dict = Depends(get_current_active_user)):
    """
    Get list of users who can receive messages.

    Used by frontend to populate recipient selection UI.
    Only accessible by Admins.
    """
    return await _get_service().get_available_recipients(current_user)


@router.get("/manager-recipients")
async def get_manager_recipients(current_user: dict = Depends(get_current_active_user)):
    """
    Get list of users a manager can message:
    - All Admins (SuperAdmin and Admin roles)
    - Employees assigned to this manager (via DutyAssignment)

    Only accessible by Site Managers.
    """
    return await _get_service().get_manager_recipients(current_user)


# =============================================================================
# UNREAD COUNT
# =============================================================================

@router.get("/unread-count")
async def get_total_unread_count(current_user: dict = Depends(get_current_active_user)):
    """
    Get total unread message count across all conversations for the current user.

    Used for notification badge in header.
    Returns: {"unread_count": <number>}
    """
    return await _get_service().get_total_unread_count(current_user)
