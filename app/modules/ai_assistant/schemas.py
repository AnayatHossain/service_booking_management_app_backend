from pydantic import BaseModel, Field
from typing import List, Optional, Any


class ChatMessage(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant|model|system)$")
    content: str


class AiChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    session_id: Optional[str] = None
    history: Optional[List[ChatMessage]] = Field(default_factory=list)
    selected_service_id: Optional[str] = None


class AiServiceSuggestion(BaseModel):
    id: str
    name: str
    category: str
    price: float
    duration_minutes: int
    image_url: str


class AiChatResponse(BaseModel):
    session_id: str
    reply: str
    response: str
    suggested_services: List[AiServiceSuggestion] = Field(default_factory=list)
    recommended_services: List[AiServiceSuggestion] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)


class AiSessionSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int
    last_message: Optional[str] = None


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "New Chat"
