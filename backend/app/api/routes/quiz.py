"""Quiz generation endpoint."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.responses import ApiResponse, QuizItem, QuizResponse
from app.services.ai_service import generate_quiz
from app.services.rag_service import get_document_content
from app.utils.logging_config import get_logger

logger = get_logger("api.quiz")

router = APIRouter(prefix="/generate-quiz", tags=["Generation"])


class GenerateQuizBody(BaseModel):
    """Request body for quiz generation."""

    document_id: str


@router.post("", response_model=ApiResponse[QuizResponse])
async def generate_quiz_endpoint(body: GenerateQuizBody):
    """Generate 5-10 MCQ questions from processed document content."""
    content = await get_document_content(body.document_id)
    if not content:
        raise HTTPException(
            status_code=404,
            detail="Document not found. Please process content first.",
        )

    try:
        items = await generate_quiz(content, body.document_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    quiz = []
    for item in items[:10]:
        q = item.get("question", "").strip()
        opts = item.get("options", [])
        correct = str(item.get("correct_answer", "A")).upper()
        exp = item.get("explanation", "").strip()
        if q and len(opts) >= 2:
            quiz.append(
                QuizItem(
                    question=q,
                    options=[str(o) for o in opts],
                    correct_answer=correct,
                    explanation=exp,
                )
            )

    if not quiz:
        raise HTTPException(
            status_code=500,
            detail="Could not generate quiz. Please try again.",
        )

    return ApiResponse(
        data=QuizResponse(
            quiz=quiz,
            document_id=body.document_id,
            count=len(quiz),
        )
    )
