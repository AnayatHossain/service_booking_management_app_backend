import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.modules.ai_assistant.schemas import AiChatRequest, ChatMessage
from app.utils.helpers import format_mongo_doc, format_mongo_docs

logger = logging.getLogger("service_booking.ai")

DEFAULT_GREETING = "Hello! I'm your AI Service Booking Assistant. How can I help you today? Ask me about available services, pricing, recommendations, or booking instructions!"
DEFAULT_QUESTIONS = [
    "What cleaning services do you have?",
    "How much is AC servicing?",
    "I need a plumber right now",
]


def _build_contextual_fallback(user_query: str, services: List[dict]) -> str:
    """Intelligent, structured fallback matching user queries against live catalog."""
    q_lower = user_query.lower()
    matched = []
    for s in services:
        name = s.get("name", "").lower()
        desc = s.get("description", "").lower()
        cat = s.get("category", "").lower()
        if any(term in name or term in desc or term in cat for term in q_lower.split() if len(term) > 2):
            matched.append(s)

    if not matched:
        matched = services[:3]

    recs = "\n".join([
        f"• **{s.get('name')}** (${s.get('price'):.2f} • {s.get('duration_minutes')} min) in *{s.get('category')}*:\n  {s.get('description', '')[:120]}..."
        for s in matched[:3]
    ])

    return (
        f"Here are the most suitable services from our catalog for you:\n\n"
        f"{recs}\n\n"
        f"💡 **How to book:** Tap on any service card below or navigate to the service to choose an available date and time slot."
    )


async def get_user_sessions(db: AsyncIOMotorDatabase, user_id: str) -> List[dict]:
    """Retrieve all chat sessions for a user sorted by most recent activity."""
    cursor = db.ai_sessions.find({"user_id": user_id}).sort("updated_at", -1).limit(50)
    docs = await cursor.to_list(length=50)

    results = []
    for doc in docs:
        doc_id = str(doc.get("_id"))
        msgs = doc.get("messages", [])
        last_msg = msgs[-1].get("text", "") if msgs else ""
        if len(last_msg) > 60:
            last_msg = last_msg[:57] + "..."

        results.append({
            "id": doc_id,
            "title": doc.get("title", "Chat Session"),
            "created_at": doc.get("created_at", ""),
            "updated_at": doc.get("updated_at", ""),
            "message_count": len(msgs),
            "last_message": last_msg
        })
    return results


async def get_session_by_id(db: AsyncIOMotorDatabase, session_id: str, user_id: str) -> dict:
    """Get full session data including all messages."""
    query = {"user_id": user_id}
    try:
        query["_id"] = ObjectId(session_id)
    except Exception:
        query["id"] = session_id

    doc = await db.ai_sessions.find_one(query)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat session not found."
        )

    doc["id"] = str(doc.pop("_id"))
    return doc


async def create_new_session(db: AsyncIOMotorDatabase, user_id: str, title: str = "New Chat") -> dict:
    """Create a new chat session."""
    now = datetime.now(timezone.utc).isoformat()
    new_doc = {
        "user_id": user_id,
        "title": title or "New Chat",
        "created_at": now,
        "updated_at": now,
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "role": "assistant",
                "text": DEFAULT_GREETING,
                "timestamp": now,
                "suggested_services": [],
                "suggested_questions": DEFAULT_QUESTIONS
            }
        ]
    }
    result = await db.ai_sessions.insert_one(new_doc)
    new_doc["id"] = str(result.inserted_id)
    new_doc.pop("_id", None)
    return new_doc


async def delete_session(db: AsyncIOMotorDatabase, session_id: str, user_id: str) -> bool:
    """Delete a single session."""
    query = {"user_id": user_id}
    try:
        query["_id"] = ObjectId(session_id)
    except Exception:
        query["id"] = session_id

    result = await db.ai_sessions.delete_one(query)
    return result.deleted_count > 0


async def clear_all_sessions(db: AsyncIOMotorDatabase, user_id: str) -> int:
    """Delete all chat sessions of a user."""
    result = await db.ai_sessions.delete_many({"user_id": user_id})
    return result.deleted_count


async def process_ai_chat(
    db: AsyncIOMotorDatabase,
    req: AiChatRequest,
    user_id: str = "guest"
) -> dict:
    now = datetime.now(timezone.utc).isoformat()

    # 1. Retrieve or create session in MongoDB
    session = None
    if req.session_id and req.session_id.strip():
        query = {"user_id": user_id}
        try:
            query["_id"] = ObjectId(req.session_id)
        except Exception:
            query["id"] = req.session_id
        session = await db.ai_sessions.find_one(query)

    if not session:
        # Create fresh session
        clean_title = req.message[:32].strip()
        if len(req.message) > 32:
            clean_title += "..."
        session_doc = {
            "user_id": user_id,
            "title": clean_title or "New Chat",
            "created_at": now,
            "updated_at": now,
            "messages": [
                {
                    "id": str(uuid.uuid4()),
                    "role": "assistant",
                    "text": DEFAULT_GREETING,
                    "timestamp": now,
                    "suggested_services": [],
                    "suggested_questions": DEFAULT_QUESTIONS
                }
            ]
        }
        ins_res = await db.ai_sessions.insert_one(session_doc)
        session_doc["_id"] = ins_res.inserted_id
        session = session_doc
    else:
        # Update title if it was default
        if session.get("title") in ["New Chat", "Chat Session", ""]:
            clean_title = req.message[:32].strip()
            if len(req.message) > 32:
                clean_title += "..."
            session["title"] = clean_title

    session_id = str(session["_id"])

    # 2. Append User Message
    user_msg_obj = {
        "id": str(uuid.uuid4()),
        "role": "user",
        "text": req.message.strip(),
        "timestamp": now,
        "suggested_services": [],
        "suggested_questions": []
    }
    session.setdefault("messages", []).append(user_msg_obj)

    # 3. Fetch live services from DB to feed as context
    cursor = db.services.find({"is_active": {"$ne": False}}).limit(35)
    services_raw = await cursor.to_list(length=35)
    services = format_mongo_docs(services_raw)

    services_summary = "\n".join([
        f"- ID: {s['id']} | Name: {s.get('name')} | Category: {s.get('category')} | Price: ${s.get('price')} | Duration: {s.get('duration_minutes')} mins | Details: {s.get('description', '')[:100]}"
        for s in services
    ])

    system_instruction = (
        "You are 'ServiceBot', the official AI Concierge for the Service Booking App powered by Gemini AI. "
        "Your mission is to provide warm, ultra-helpful, highly accurate assistance for customer queries about "
        "services, booking steps, pricing, durations, categories, and recommendations.\n\n"
        "Here is the official live catalog of available services:\n"
        f"{services_summary}\n\n"
        "Instructions:\n"
        "1. Recommend matching services from the catalog by exact name, price, and category.\n"
        "2. Provide clear, structured, readable responses with bullet points and bold highlights.\n"
        "3. Explain that users can book appointments directly by choosing any service card and selecting a slot.\n"
        "4. If a requested service does not exist, recommend the closest alternative from the catalog politely."
    )

    # Find matching services to attach as cards
    suggested_services = []
    q_words = req.message.lower().split()
    for s in services:
        name_lower = s.get("name", "").lower()
        cat_lower = s.get("category", "").lower()
        desc_lower = s.get("description", "").lower()
        if any(w in name_lower or w in cat_lower or w in desc_lower for w in q_words if len(w) > 2):
            suggested_services.append({
                "id": s["id"],
                "name": s["name"],
                "category": s["category"],
                "price": float(s["price"]),
                "duration_minutes": int(s["duration_minutes"]),
                "image_url": s.get("image_url", "")
            })

    if not suggested_services and services:
        suggested_services = [
            {
                "id": s["id"],
                "name": s["name"],
                "category": s["category"],
                "price": float(s["price"]),
                "duration_minutes": int(s["duration_minutes"]),
                "image_url": s.get("image_url", "")
            }
            for s in services if s.get("is_featured")
        ][:2]

    reply_text = None

    # 4. Call Gemini API if API key is configured
    if settings.gemini_api_key and settings.gemini_api_key.strip():
        contents = [
            {"role": "user", "parts": [{"text": system_instruction}]},
            {"role": "model", "parts": [{"text": "Understood! I am ready to serve as the intelligent AI Concierge for the Service Booking platform."}]}
        ]

        # Add recent conversation history from this session
        history_msgs = session["messages"][-7:-1]
        for m in history_msgs:
            role = "user" if m.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m.get("text", "")}]})

        contents.append({"role": "user", "parts": [{"text": req.message}]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"

        try:
            async with httpx.AsyncClient(timeout=14.0) as client:
                res = await client.post(
                    url,
                    json={
                        "contents": contents,
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 800,
                        }
                    }
                )
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            reply_text = parts[0]["text"]
                else:
                    logger.warning(f"Gemini API returned status {res.status_code}: {res.text[:150]}")
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")

    # 5. Fallback response if Gemini API was unavailable
    if not reply_text:
        reply_text = _build_contextual_fallback(req.message, services)

    suggested_questions = [
        "What are your most popular services?",
        "How do I book an appointment?",
        "What is the cancellation policy?",
        "Can I reschedule a booking?"
    ]

    # 6. Append Assistant Message to Session
    bot_msg_obj = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "text": reply_text,
        "timestamp": now,
        "suggested_services": suggested_services[:3],
        "suggested_questions": suggested_questions
    }
    session["messages"].append(bot_msg_obj)

    # 7. Persist to MongoDB
    await db.ai_sessions.update_one(
        {"_id": session["_id"]},
        {
            "$set": {
                "title": session.get("title", "Chat"),
                "messages": session["messages"],
                "updated_at": now
            }
        },
        upsert=True
    )

    return {
        "session_id": session_id,
        "reply": reply_text,
        "response": reply_text,  # compatibility
        "suggested_services": suggested_services[:3],
        "recommended_services": suggested_services[:3],  # compatibility
        "suggested_questions": suggested_questions,
        "session_title": session.get("title", "Chat")
    }
