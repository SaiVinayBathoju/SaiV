"""RAG (Retrieval-Augmented Generation) service using Supabase pgvector."""

import traceback
from typing import List, Optional

from supabase import create_client, Client

from app.config import get_settings
from app.services.embeddings import generate_embeddings
from app.utils.chunking import chunk_text
from app.utils.logging_config import get_logger

logger = get_logger("rag")


def get_supabase_client() -> Client:
    """Create Supabase client. No proxy or custom httpx passed."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_key:
        raise ValueError("Supabase URL and service key must be configured")
    try:
        return create_client(settings.supabase_url, settings.supabase_service_key)
    except TypeError as e:
        if "proxy" in str(e).lower() or "proxies" in str(e).lower():
            traceback.print_exc()
            raise ValueError(
                "Supabase/httpx version conflict. Install: pip install 'supabase>=2.10' 'httpx>=0.26,<0.28'"
            ) from e
        raise


async def upsert_document(
    document_id: str,
    source_type: str,
    source_id: str,
    title: str,
    content: str,
    metadata: Optional[dict] = None,
) -> int:
    """
    Store document and its chunks with embeddings in Supabase.
    Returns number of chunks stored.
    """
    settings = get_settings()
    client = get_supabase_client()

    chunks = chunk_text(
        content,
        chunk_size=settings.max_chunk_size,
        overlap=settings.chunk_overlap,
    )
    if not chunks:
        raise ValueError("No chunks generated from content")

    embeddings = await generate_embeddings(chunks)

    # Insert document (each processing creates a new document)
    client.table("documents").insert(
        {
            "id": document_id,
            "source_type": source_type,
            "source_id": source_id,
            "title": title,
            "content": content,
            "metadata": metadata or {},
        }
    ).execute()

    # Delete existing chunks for this document
    client.table("document_chunks").delete().eq("document_id", document_id).execute()

    # Insert chunks with embeddings
    rows = [
        {
            "document_id": document_id,
            "chunk_index": i,
            "content": chunk,
            "embedding": emb,
            "metadata": {},
        }
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings))
    ]

    for row in rows:
        client.table("document_chunks").insert(row).execute()

    logger.info("Document indexed", document_id=document_id, chunks=len(chunks))
    return len(chunks)


async def retrieve_context(
    document_id: str,
    query: str,
    top_k: Optional[int] = None,
) -> str:
    """
    Retrieve relevant chunks for a query using vector similarity.
    Returns concatenated context string.
    """
    settings = get_settings()
    client = get_supabase_client()
    top_k = top_k or settings.max_retrieval_chunks

    # Generate query embedding
    query_embeddings = await generate_embeddings([query])
    query_embedding = query_embeddings[0]

    # Supabase pgvector RPC for similarity search
    # Using match_document_chunks RPC - we need to create it, or use raw SQL
    # Supabase Python client supports rpc() for stored procedures
    result = client.rpc(
        "match_document_chunks",
        {
            "query_embedding": query_embedding,
            "match_document_id": document_id,
            "match_count": top_k,
        },
    ).execute()

    if not result.data:
        # Fallback: if RPC doesn't exist, we'll need to create it
        # For now, fetch chunks and do client-side similarity (not ideal)
        # Better: ensure the RPC exists in schema
        chunks_result = (
            client.table("document_chunks")
            .select("content")
            .eq("document_id", document_id)
            .limit(top_k * 2)  # Get more, we can't rank without RPC
            .execute()
        )
        chunks = [r["content"] for r in (chunks_result.data or [])]
        return "\n\n---\n\n".join(chunks[:top_k]) if chunks else ""

    chunks = [r["content"] for r in result.data]
    return "\n\n---\n\n".join(chunks) if chunks else ""


async def get_document_content(document_id: str) -> Optional[str]:
    """Fetch full document content by ID."""
    client = get_supabase_client()
    result = (
        client.table("documents")
        .select("content")
        .eq("id", document_id)
        .single()
        .execute()
    )
    if result.data:
        return result.data.get("content")
    return None
