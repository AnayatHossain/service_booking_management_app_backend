from pydantic import BaseModel, Field
from typing import List, Optional


class ChatMessage(BaseModel):
    role: str = Field(..., pattern=r"^(user|assistant|model|system)$")
    content: str


class AiChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
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
    reply: str
    suggested_services: List[AiServiceSuggestion] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)
