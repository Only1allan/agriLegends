from fastapi import APIRouter
from pydantic import BaseModel
from agents.chat_agent import chat_query

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    farmerId: str
    message: str
    history: list[ChatMessage] | None = None


class ChatResponse(BaseModel):
    answer: str
    cypher: str | None = None
    results: list | None = None
    confidence: str = "medium"


@router.post("/query")
async def chat_endpoint(req: ChatRequest) -> ChatResponse:
    result = await chat_query(req.farmerId, req.message)
    return ChatResponse(**result)
