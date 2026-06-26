from fastapi import APIRouter
from pydantic import BaseModel
from agents.tts import generate_swahili_audio

router = APIRouter()


class TTSRequest(BaseModel):
    text: str
    language: str = "swahili"


class TTSResponse(BaseModel):
    audioUrl: str
    swahiliText: str


@router.post("/generate")
async def generate_tts(req: TTSRequest) -> TTSResponse:
    result = await generate_swahili_audio(req.text)
    return TTSResponse(audioUrl=result["audioUrl"], swahiliText=result["swahiliText"])
