"""Video processing endpoint."""

import traceback
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.responses import ApiResponse, ProcessContentResponse
from app.services.rag_service import upsert_document
from app.services.youtube import extract_video_id, fetch_transcript
from app.utils.logging_config import get_logger

logger = get_logger("api.video")

router = APIRouter(prefix="/process-video", tags=["Content"])


class ProcessVideoBody(BaseModel):
    """Request body for video processing."""

    url: str


@router.post("", response_model=ApiResponse[ProcessContentResponse])
async def process_video(body: ProcessVideoBody):
    """Process a YouTube video: fetch transcript and index for RAG."""
    try:
        video_id = extract_video_id(body.url)
        if not video_id:
            raise HTTPException(
                status_code=400,
                detail="Invalid YouTube URL. Please provide a valid YouTube video link.",
            )

        # Fetch transcript (may raise ValueError with a user-friendly message)
        title, content = fetch_transcript(body.url)
        if not content.strip():
            raise HTTPException(
                status_code=400,
                detail="Transcript is empty. The video may not have usable captions.",
            )

        document_id = str(uuid.uuid4())

        chunk_count = await upsert_document(
            document_id=document_id,
            source_type="youtube",
            source_id=video_id,
            title=title,
            content=content,
            metadata={"url": body.url, "video_id": video_id},
        )

        preview = content[:500] + ("..." if len(content) > 500 else "")
        return ApiResponse(
            data=ProcessContentResponse(
                document_id=document_id,
                title=title,
                content_preview=preview,
                chunk_count=chunk_count,
                message="Video transcript processed and indexed successfully.",
            )
        )
    except ValueError as e:
        logger.warning("Video processing validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        # Already has correct status/detail
        raise
    except Exception as e:
        traceback.print_exc()
        logger.exception("Video processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
