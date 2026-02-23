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
    valid_letters = ("A", "B", "C", "D")
    for item in items[:10]:
        q = (item.get("question") or "").strip()
        opts_raw = item.get("options") or []
        opts = [str(o).strip() for o in opts_raw] if isinstance(opts_raw, list) else []
        if not q or len(opts) < 2:
            continue
        correct = str(item.get("correct_answer") or "A").strip().upper()
        if correct not in valid_letters:
            correct = "A"
        exp = (item.get("explanation") or "").strip()
        quiz.append(
            QuizItem(
                question=q,
                options=opts,
                correct_answer=correct,
                explanation=exp,
            )
        )

    return ApiResponse(
        data=QuizResponse(
            quiz=quiz,
            document_id=body.document_id,
            count=len(quiz),
        )
    )
