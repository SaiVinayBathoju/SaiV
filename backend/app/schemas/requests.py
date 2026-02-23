"""Request schemas for API validation."""

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ProcessVideoRequest(BaseModel):
    """Request body for processing a YouTube video."""

    url: HttpUrl = Field(..., description="YouTube video URL")


class ProcessPdfRequest(BaseModel):
    """Request for PDF processing - file sent via multipart form."""

    pass  # File comes via UploadFile in endpoint


class GenerateFlashcardsRequest(BaseModel):
    """Request for flashcard generation."""

    document_id: str = Field(..., description="ID of processed document")
    content: str = Field(..., description="Extracted text content for generation")


class GenerateQuizRequest(BaseModel):
    """Request for quiz generation."""

    document_id: str = Field(..., description="ID of processed document")
    content: str = Field(..., description="Extracted text content for generation")


class ChatMessage(BaseModel):
    """Single chat message."""

    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    """Request for RAG chat."""

    document_id: str = Field(..., description="ID of document to use as context")
    messages: List[ChatMessage] = Field(
        ..., min_length=1, description="Conversation history"
    )
