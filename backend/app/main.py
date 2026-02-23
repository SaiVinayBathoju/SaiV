"""SaiV FastAPI application entry point."""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, flashcards, pdf, quiz, video
from app.config import get_settings
from app.utils.logging_config import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Load environment variables from .env before anything else
    load_dotenv()
    configure_logging()
    get_logger("main").info("SaiV API starting")
    yield
    get_logger("main").info("SaiV API shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        description="AI Learning Assistant - Process content, generate flashcards, quizzes, and chat with RAG",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routes
    app.include_router(video.router)
    app.include_router(pdf.router)
    app.include_router(flashcards.router)
    app.include_router(quiz.router)
    app.include_router(chat.router)

    @app.get("/")
    async def root():
        """Root endpoint - API info."""
        return {
            "service": "SaiV API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health",
            "endpoints": [
                "POST /process-video",
                "POST /process-pdf",
                "POST /generate-flashcards",
                "POST /generate-quiz",
                "POST /chat",
            ],
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok", "service": "saiv-api"}

    return app


app = create_app()
