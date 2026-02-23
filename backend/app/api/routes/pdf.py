"""PDF processing endpoint."""

import hashlib
import traceback
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.schemas.responses import ApiResponse, ProcessContentResponse
from app.services.pdf_extractor import extract_text_from_pdf
from app.services.rag_service import upsert_document
from app.utils.logging_config import get_logger

logger = get_logger("api.pdf")

router = APIRouter(prefix="/process-pdf", tags=["Content"])


@router.post("", response_model=ApiResponse[ProcessContentResponse])
async def process_pdf(file: UploadFile = File(..., alias="file")):
    """Process uploaded PDF: extract text and index for RAG."""
    filename = (file.filename or "").strip() or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file. Please upload a PDF file.",
        )

    try:
        # Read raw bytes from upload
        content_bytes = await file.read()
    except Exception as e:
        traceback.print_exc()
        logger.warning("PDF read failed", error=str(e))
        raise HTTPException(
            status_code=400,
            detail="Could not read file. The file may be corrupted or too large.",
        )

    if not content_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(content_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB.",
        )

    # Extract text
    try:
        title, text = extract_text_from_pdf(content_bytes, filename)
    except ValueError as e:
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

    if not text.strip():
        raise HTTPException(
            status_code=400,
            detail="No readable text could be extracted from this PDF.",
        )

    document_id = str(uuid.uuid4())
    source_id = hashlib.sha256(content_bytes[:1024]).hexdigest()[:32]

    try:
        chunk_count = await upsert_document(
            document_id=document_id,
            source_type="pdf",
            source_id=source_id,
            title=title,
            content=text,
            metadata={"filename": filename},
        )
    except Exception as e:
        traceback.print_exc()
        # Surface Supabase / embedding / config errors clearly
        raise HTTPException(status_code=500, detail=str(e))

    preview = text[:500] + ("..." if len(text) > 500 else "")
    return ApiResponse(
        data=ProcessContentResponse(
            document_id=document_id,
            title=title,
            content_preview=preview,
            chunk_count=chunk_count,
            message="PDF processed and indexed successfully.",
        )
    )
