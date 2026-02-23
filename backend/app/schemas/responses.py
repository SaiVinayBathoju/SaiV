"""Response schemas for API responses."""

from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper."""

    success: bool = True
    data: Optional[T] = None
    error: Optional[str] = None
    message: Optional[str] = None


class ProcessContentResponse(BaseModel):
    """Response for content processing (video/PDF)."""

    document_id: str
    title: str
    content_preview: str = Field(
        ..., description="First 500 chars of content for preview"
    )
    chunk_count: int
    message: str = "Content processed and indexed successfully"


class FlashcardItem(BaseModel):
    """Single flashcard."""

    question: str
    answer: str


class FlashcardsResponse(BaseModel):
    """Response for flashcard generation."""

    flashcards: List[FlashcardItem]
    document_id: str
    count: int


class QuizItem(BaseModel):
    """Single quiz question."""

    question: str
    options: List[str] = Field(..., min_length=2, max_length=6)
    correct_answer: str  # Index letter: A, B, C, D, etc.
    explanation: str


class QuizResponse(BaseModel):
    """Response for quiz generation."""

    quiz: List[QuizItem]
    document_id: str
    count: int


class ChatResponse(BaseModel):
    """Response for chat - used for non-streaming; streaming uses SSE."""

    message: str
    sources: Optional[List[str]] = None
