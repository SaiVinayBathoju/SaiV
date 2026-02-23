"""Chat endpoint with RAG and streaming."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.ai_service import chat_completion_stream
from app.services.rag_service import retrieve_context
from app.utils.logging_config import get_logger

logger = get_logger("api.chat")

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatMessage(BaseModel):
    """Single message in conversation."""

    role: str  # "user" | "assistant"
    content: str


class ChatBody(BaseModel):
    """Request body for chat."""

    document_id: str
    messages: list[ChatMessage]


def _sse_format(data: str) -> str:
    """Format string as SSE event. Multi-line becomes multiple data: lines."""
    lines = data.split("\n")
    return "".join(f"data: {line}\n" for line in lines) + "\n"


async def _stream_generator(document_id: str, messages: list[ChatMessage]):
    """Generate SSE stream for chat response."""
    if not messages:
        yield _sse_format("[ERROR]No messages provided")
        return
    last_msg = messages[-1]
    if last_msg.role != "user":
        yield _sse_format("[ERROR]Last message must be from user")
        return

    try:
        context = await retrieve_context(document_id, last_msg.content)
        if not context:
            context = "No relevant context found. The document may not be indexed yet."
    except ValueError as e:
        yield _sse_format(f"[ERROR]{str(e)}")
        return

    try:
        msgs = [{"role": m.role, "content": m.content} for m in messages]
        async for chunk in chat_completion_stream(msgs, context):
            yield _sse_format(chunk)
    except Exception as e:
        logger.exception("Chat stream failed")
        yield _sse_format(f"[ERROR]Chat failed: {str(e)}")


@router.post("")
async def chat(body: ChatBody):
    """Stream RAG-grounded chat responses."""
    try:
        return StreamingResponse(
            _stream_generator(body.document_id, body.messages),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        logger.exception("Chat endpoint error")
        raise HTTPException(status_code=500, detail=str(e))
