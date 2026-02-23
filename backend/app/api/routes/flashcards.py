"""Flashcard generation endpoint."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.responses import ApiResponse, FlashcardItem, FlashcardsResponse
from app.services.ai_service import generate_flashcards
from app.services.rag_service import get_document_content
from app.utils.logging_config import get_logger

logger = get_logger("api.flashcards")

router = APIRouter(prefix="/generate-flashcards", tags=["Generation"])


class GenerateFlashcardsBody(BaseModel):
    """Request body for flashcard generation."""

    document_id: str


@router.post("", response_model=ApiResponse[FlashcardsResponse])
async def generate_flashcards_endpoint(body: GenerateFlashcardsBody):
    """Generate 10-15 flashcards from processed document content."""
    content = await get_document_content(body.document_id)
    if not content:
        raise HTTPException(
            status_code=404,
            detail="Document not found. Please process content first.",
        )

    try:
        items = await generate_flashcards(content, body.document_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Normalize to our schema
    flashcards = []
    for item in items[:15]:  # Cap at 15
        q = item.get("question", "").strip()
        a = item.get("answer", "").strip()
        if q and a:
            flashcards.append(FlashcardItem(question=q, answer=a))

    if not flashcards:
        raise HTTPException(
            status_code=500,
            detail="Could not generate flashcards. Please try again.",
        )

    return ApiResponse(
        data=FlashcardsResponse(
            flashcards=flashcards,
            document_id=body.document_id,
            count=len(flashcards),
        )
    )
