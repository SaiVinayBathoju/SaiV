"""Embedding generation service: OpenAI, Gemini (free), and optional local (fastembed) fallback."""

import asyncio
import math
import traceback
from typing import List

from app.config import get_settings
from app.utils.logging_config import get_logger

logger = get_logger("embeddings")

# gemini-embedding-001 default is 3072; we request 1536 via output_dimensionality or pad to target_dim
GEMINI_EMBED_DIM = 3072
# Local model output dimension (fastembed BAAI/bge-small-en-v1.5)
LOCAL_EMBED_DIM = 384


def _pad_and_normalize(vectors: List[List[float]], target_dim: int) -> List[List[float]]:
    """Pad or truncate vectors to target_dim and L2-normalize."""
    result: List[List[float]] = []
    for arr in vectors:
        if len(arr) < target_dim:
            arr = arr + [0.0] * (target_dim - len(arr))
        else:
            arr = arr[:target_dim]
        norm = math.sqrt(sum(x * x for x in arr)) or 1.0
        result.append([x / norm for x in arr])
    return result


def _embed_gemini_sync(texts: List[str], target_dim: int) -> List[List[float]]:
    """Generate embeddings using Gemini (sync). Pads to target_dim and L2-normalizes."""
    import google.generativeai as genai
    from google.generativeai import embedding as genai_embedding

    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = settings.gemini_embedding_model
    # Batch in sizes the API accepts; request 1536 dims when supported (gemini-embedding-001)
    batch_size = 100
    all_embeddings: List[List[float]] = []
    kwargs = {"model": model, "content": None, "task_type": "retrieval_document"}
    if target_dim in (768, 1536, 3072):
        kwargs["output_dimensionality"] = target_dim
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        kwargs["content"] = batch
        result = genai_embedding.embed_content(**kwargs)
        # result["embedding"] is list of lists for batch input, or single list for one text
        batch_emb = result.get("embedding", [])
        if batch_emb and isinstance(batch_emb[0], (int, float)):
            batch_emb = [batch_emb]
        all_embeddings.extend(batch_emb)
    return _pad_and_normalize(all_embeddings, target_dim)


def _embed_local_sync(texts: List[str], target_dim: int) -> List[List[float]]:
    """Generate embeddings using fastembed (sync). Pads to target_dim and L2-normalizes."""
    try:
        from fastembed import TextEmbedding
    except ImportError:
        raise ValueError(
            "Local embedding fallback requires 'fastembed'. Install with: pip install fastembed. "
            "Or set OPENAI_API_KEY / use Gemini and disable EMBEDDING_FALLBACK_TO_LOCAL on hosted deployments."
        ) from None

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


def _gemini_available() -> bool:
    return bool(get_settings().gemini_api_key)


async def _generate_embeddings_gemini(texts: List[str], target_dim: int) -> List[List[float]]:
    """Run sync Gemini embedding in executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: _embed_gemini_sync(texts, target_dim),
    )


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of text chunks.
    Order: OpenAI (if key set) -> on failure or no key, Gemini (if key set) -> else local fastembed if enabled.
    """
    if not texts:
        return []

    settings = get_settings()
    target_dim = settings.embedding_dimensions

    # 1) Try OpenAI when key is set
    if settings.openai_api_key:
        try:
            from openai import AsyncOpenAI
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
                all_embeddings.extend([item.embedding for item in response.data])
            return all_embeddings
        except Exception as e:
            traceback.print_exc()
            err_str = str(e).lower()
            is_invalid_key = "401" in err_str or "invalid_api_key" in err_str or "incorrect api key" in err_str
            if is_invalid_key:
                logger.warning("OpenAI API key invalid or rejected; trying Gemini for embeddings", error=str(e))
            else:
                logger.warning("OpenAI embedding failed; trying Gemini for embeddings", error=str(e))
            # Fall through to try Gemini or local
    else:
        logger.info("No OpenAI API key; using Gemini or local for embeddings")

    # 2) Try Gemini (free tier) when key is set
    if _gemini_available():
        try:
            return await _generate_embeddings_gemini(texts, target_dim)
        except Exception as e:
            traceback.print_exc()
            logger.warning("Gemini embedding failed", error=str(e))
            if not settings.embedding_fallback_to_local:
                raise ValueError(f"Embedding generation failed: {e}") from e
    else:
        if not settings.embedding_fallback_to_local:
            raise ValueError(
                "No embedding provider available. Set OPENAI_API_KEY, or GEMINI_API_KEY (free at https://aistudio.google.com/apikey), "
                "or enable EMBEDDING_FALLBACK_TO_LOCAL and install fastembed."
            ) from None

    # 3) Local fallback (fastembed) if enabled
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        lambda: _embed_local_sync(texts, target_dim),
    )
