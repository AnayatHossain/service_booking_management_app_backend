from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.responses import success_response
from app.modules.ai_assistant.schemas import AiChatRequest
from app.modules.ai_assistant.service import process_ai_chat

router = APIRouter(prefix="/api/ai", tags=["AI Assistant"])


@router.post("/chat", summary="Interact with the AI Service Assistant")
async def chat_with_assistant(
    req: AiChatRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    result = await process_ai_chat(db, req)
    return success_response(
        data=result,
        message="AI response generated successfully."
    )


@router.get("/prompts", summary="Get quick conversation starter prompts")
async def get_quick_prompts():
    prompts = [
        "Recommend a relaxing spa or wellness service.",
        "What are your best cleaning services?",
        "Can you suggest a quick 30-minute grooming session?",
        "How do I cancel or reschedule my appointment?",
        "Which service has the highest customer rating?"
    ]
    return success_response(
        data=prompts,
        message="Quick prompts retrieved."
    )
