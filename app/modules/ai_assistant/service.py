import json
import logging
import httpx
from typing import List, Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings
from app.modules.ai_assistant.schemas import AiChatRequest, ChatMessage
from app.utils.helpers import format_mongo_docs

logger = logging.getLogger("service_booking.ai")


def _build_contextual_fallback(user_query: str, services: List[dict]) -> str:
    """Intelligent fallback when Google API has high load or network issues."""
    q_lower = user_query.lower()
    matched = []
    for s in services:
        name = s.get("name", "").lower()
        desc = s.get("description", "").lower()
        cat = s.get("category", "").lower()
        if any(term in name or term in desc or term in cat for term in q_lower.split()):
            matched.append(s)

    if not matched:
        matched = services[:3]

    recs = "\n".join([
        f"• **{s.get('name')}** (${s.get('price')} - {s.get('duration_minutes')} min) in {s.get('category')}: {s.get('description')[:100]}..."
        for s in matched[:3]
    ])

    return (
        f"Here are the most suitable services based on your request:\n\n"
        f"{recs}\n\n"
        f"You can view complete details and book an appointment directly from the app."
    )


async def process_ai_chat(
    db: AsyncIOMotorDatabase,
    req: AiChatRequest
) -> dict:
    # 1. Fetch available services from DB to feed as context
    cursor = db.services.find({"is_active": {"$ne": False}}).limit(30)
    services_raw = await cursor.to_list(length=30)
    services = format_mongo_docs(services_raw)

    services_summary = "\n".join([
        f"- ID: {s['id']} | Name: {s.get('name')} | Category: {s.get('category')} | Price: ${s.get('price')} | Duration: {s.get('duration_minutes')} mins | Details: {s.get('description')}"
        for s in services
    ])

    system_instruction = (
        "You are 'ServiceBot', an intelligent, warm, and helpful AI assistant for the Service Booking App. "
        "Your mission is to help customers explore services, answer pricing/duration questions, and give tailored recommendations. "
        "Below is our live catalog of available services:\n"
        f"{services_summary}\n\n"
        "Guidelines:\n"
        "1. Recommend matching services from the catalog by exact name, price, and duration.\n"
        "2. Explain how to book them (select an available date/time slot on the booking screen).\n"
        "3. Keep your answers concise, structured (bullet points), polite, and encouraging.\n"
        "4. If a service is not in the catalog, politely let the customer know and offer the closest match."
    )

    # Find matching services to attach as cards
    suggested_services = []
    q_words = req.message.lower().split()
    for s in services:
        name_lower = s.get("name", "").lower()
        cat_lower = s.get("category", "").lower()
        if any(w in name_lower or w in cat_lower for w in q_words if len(w) > 3):
            suggested_services.append({
                "id": s["id"],
                "name": s["name"],
                "category": s["category"],
                "price": float(s["price"]),
                "duration_minutes": int(s["duration_minutes"]),
                "image_url": s.get("image_url", "")
            })
    if not suggested_services and services:
        # Default to featured services if no specific keyword matched
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

    # 2. Call Gemini API if key is available
    if settings.gemini_api_key and settings.gemini_api_key.strip():
        # Build contents array
        contents = [
            {"role": "user", "parts": [{"text": system_instruction}]},
            {"role": "model", "parts": [{"text": "Understood! I am ServiceBot, ready to help customers find and book the perfect services from your catalog."}]}
        ]

        if req.history:
            for h in req.history[-6:]:
                role = "user" if h.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": h.content}]})

        contents.append({"role": "user", "parts": [{"text": req.message}]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
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

    # 3. Graceful fallback if Gemini did not respond
    if not reply_text:
        reply_text = _build_contextual_fallback(req.message, services)

    suggested_questions = [
        "What are your most popular services?",
        "How do I book an appointment?",
        "What is the cancellation policy?",
        "Can I reschedule a booking?"
    ]

    return {
        "reply": reply_text,
        "suggested_services": suggested_services[:3],
        "suggested_questions": suggested_questions
    }
