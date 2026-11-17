from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.deps import get_optional_user
from app.core.responses import success_response
from app.modules.ai_assistant.schemas import (
    AiChatRequest,
    CreateSessionRequest
)
from app.modules.ai_assistant.service import (
    process_ai_chat,
    get_user_sessions,
    get_session_by_id,
    create_new_session,
    delete_session,
    clear_all_sessions
)

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])


def _extract_user_id(current_user: Optional[dict]) -> str:
    if current_user and "id" in current_user:
        return str(current_user["id"])
    return "guest_user"


@router.post("/chat", summary="Interact with the AI Service Assistant")
async def chat_with_assistant(
    req: AiChatRequest,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = _extract_user_id(current_user)
    result = await process_ai_chat(db, req, user_id=user_id)
    return success_response(
        data=result,
        message="AI response generated successfully."
    )


@router.get("/sessions", summary="Get all chat sessions for user")
async def list_chat_sessions(
    current_user: Optional[dict] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = _extract_user_id(current_user)
    sessions = await get_user_sessions(db, user_id=user_id)
    return success_response(
        data=sessions,
        message="Chat sessions retrieved."
    )


@router.post("/sessions", summary="Create a new empty chat session")
async def create_chat_session(
    body: Optional[CreateSessionRequest] = None,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = _extract_user_id(current_user)
    title = body.title if body else "New Chat"
    session = await create_new_session(db, user_id=user_id, title=title)
    return success_response(
        data=session,
        message="New chat session created."
    )


@router.get("/sessions/{session_id}", summary="Get messages for a specific session")
async def get_session_details(
    session_id: str,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = _extract_user_id(current_user)
    session = await get_session_by_id(db, session_id=session_id, user_id=user_id)
    return success_response(
        data=session,
        message="Chat session details retrieved."
    )


@router.delete("/sessions/{session_id}", summary="Delete a specific chat session")
async def delete_chat_session(
    session_id: str,
    current_user: Optional[dict] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = _extract_user_id(current_user)
    deleted = await delete_session(db, session_id=session_id, user_id=user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already deleted."
        )
    return success_response(
        data={"deleted": True, "session_id": session_id},
        message="Chat session deleted successfully."
    )


@router.delete("/sessions", summary="Clear all chat sessions")
async def clear_chat_history(
    current_user: Optional[dict] = Depends(get_optional_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    user_id = _extract_user_id(current_user)
    count = await clear_all_sessions(db, user_id=user_id)
    return success_response(
        data={"deleted_count": count},
        message="All chat sessions cleared successfully."
    )


@router.get("/prompts", summary="Get quick conversation starter prompts")
async def get_quick_prompts():
    prompts = [
        "What cleaning services do you have?",
        "How much is AC servicing?",
        "I need a plumber right now",
        "Recommend a relaxing spa or wellness service.",
        "How do I cancel or reschedule my appointment?",
        "Which service has the highest customer rating?"
    ]
    return success_response(
        data=prompts,
        message="Quick prompts retrieved."
    )
