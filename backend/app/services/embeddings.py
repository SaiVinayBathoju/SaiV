"""Embedding generation service with OpenAI and local (fastembed) fallback."""

import asyncio
import math
import traceback
from typing import List

from openai import AsyncOpenAI

from app.config import get_settings
from app.utils.logging_config import get_logger

logger = get_logger("embeddings")

# Local model output dimension (fastembed BAAI/bge-small-en-v1.5)
LOCAL_EMBED_DIM = 384


def _embed_local_sync(texts: List[str], target_dim: int) -> List[List[float]]:
    """Generate embeddings using fastembed (sync). Pads to target_dim and L2-normalizes."""
    from fastembed import TextEmbedding

    model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", max_length=512)
    # embed returns an iterable of ndarrays
    raw = list(model.embed(texts))
    result: List[List[float]] = []
    for vec in raw:
        arr = vec.tolist() if hasattr(vec, "tolist") else list(vec)
        # Pad to target_dim with zeros
        if len(arr) < target_dim:
            arr = arr + [0.0] * (target_dim - len(arr))
        else:
            arr = arr[:target_dim]
        # L2-normalize so cosine similarity works correctly with padded vectors
        norm = math.sqrt(sum(x * x for x in arr)) or 1.0
        result.append([x / norm for x in arr])
    return result


async def _generate_embeddings_openai(texts: List[str]) -> List[List[float]]:
    """Call OpenAI embeddings API. Raises on failure."""
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    batch_size = 100
    all_embeddings: List[List[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
            dimensions=settings.embedding_dimensions,
        )
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)
    return all_embeddings


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of text chunks.
    Uses OpenAI when available; on quota/rate-limit or missing key, falls back to local
    (fastembed) if embedding_fallback_to_local is True.
    """
    if not texts:
        return []

    settings = get_settings()
    target_dim = settings.embedding_dimensions

    # Prefer OpenAI when key is set (no proxy or custom httpx)
    if settings.openai_api_key:
        try:
            return await _generate_embeddings_openai(texts)
        except Exception as e:
            traceback.print_exc()
            err_str = str(e).lower()
            is_quota_or_rate = (
                "429" in err_str
                or "insufficient_quota" in err_str
                or "rate limit" in err_str
            )
            if is_quota_or_rate:
                logger.warning(
                    "OpenAI embedding quota/rate limit hit, falling back to local embeddings",
                    error=str(e),
                )
            else:
                logger.warning(
                    "OpenAI embedding failed, falling back to local embeddings",
                    error=str(e),
                )
            if not settings.embedding_fallback_to_local:
                raise ValueError(f"Embedding generation failed: {e}") from e
            # Fall through to local
    else:
        if not settings.embedding_fallback_to_local:
            raise ValueError(
                "OpenAI API key not configured and local embedding fallback is disabled. "
                "Set OPENAI_API_KEY or EMBEDDING_FALLBACK_TO_LOCAL=true."
            )
        logger.info("No OpenAI API key; using local embeddings")

    # Local fallback: run sync fastembed in thread pool, pad and normalize to target_dim
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: _embed_local_sync(texts, target_dim),
    )
