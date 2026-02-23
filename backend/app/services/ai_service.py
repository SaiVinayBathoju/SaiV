"""AI/LLM service: OpenAI and Google Gemini (free tier) support."""

import asyncio
import json
import re
import traceback
from typing import AsyncGenerator, List

from app.config import get_settings
from app.utils.logging_config import get_logger

logger = get_logger("ai")

QUOTA_EXCEEDED_MESSAGE = (
    "Your OpenAI account has run out of quota or has no billing set up. "
    "Using Gemini free tier instead. Set GEMINI_API_KEY in .env for free usage "
    "(get key at https://aistudio.google.com/apikey)."
)


def _raise_if_quota_error(e: Exception) -> None:
    msg = str(e).lower()
    if "429" in msg or "insufficient_quota" in msg or "quota" in msg or "billing" in msg:
        raise ValueError(QUOTA_EXCEEDED_MESSAGE) from e


def _parse_json_array(text: str, label: str) -> List[dict]:
    """Parse JSON array from model output, stripping markdown code fences if present."""
    raw = text.strip()
    text = raw
    # Strip markdown code block: ```json ... ``` or ``` ... ```
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()
        else:
            # No closing ``` (truncated or single fence): strip leading fence and take rest
            if text.startswith("```"):
                text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            if text.endswith("```"):
                text = re.sub(r"\n?```\s*$", "", text)
            text = text.strip()
    # If still not valid JSON, try extracting array between first [ and last ]
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, list) else []
            except json.JSONDecodeError:
                pass
        logger.warning(f"Failed to parse {label} JSON", error="invalid or truncated", raw=raw[:200])
        return []


# ---------- Gemini (free tier) ----------

def _gemini_available() -> bool:
    return bool(get_settings().gemini_api_key)


def _gemini_generate_sync(prompt: str, system_instruction: str | None = None, max_tokens: int = 2048) -> str:
    """Sync Gemini call (run in executor)."""
    import google.generativeai as genai
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        settings.gemini_model,
        system_instruction=system_instruction or "You are a helpful assistant. Respond with clear, concise text.",
    )
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=0.5,
        ),
    )
    if not response or not response.text:
        return ""
    return response.text.strip()


def _gemini_stream_sync(prompt: str, system_instruction: str | None) -> List[str]:
    """Sync Gemini stream; returns list of text chunks (run in executor)."""
    import google.generativeai as genai
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        settings.gemini_model,
        system_instruction=system_instruction or "You are a helpful assistant.",
    )
    chunks = []
    for chunk in model.generate_content(prompt, stream=True):
        if chunk.text:
            chunks.append(chunk.text)
    return chunks


async def _generate_flashcards_gemini(content: str, document_id: str) -> List[dict]:
    settings = get_settings()
    max_chars = 12000
    truncated = content[:max_chars] + ("..." if len(content) > max_chars else "")
    system = """You are an expert educational content designer. Generate high-quality flashcards from the given learning material.
Rules: Generate 10-15 flashcards. Each question targets a key concept; answers are concise (1-3 sentences). No duplicates.
Return ONLY a valid JSON array, no markdown: [{"question": "...", "answer": "..."}, ...]"""
    user = f"Create flashcards from this content:\n\n{truncated}\n\nReturn a JSON array of flashcards."
    loop = asyncio.get_event_loop()
    text = await loop.run_in_executor(
        None,
        lambda: _gemini_generate_sync(user, system, max_tokens=2000),
    )
    return _parse_json_array(text or "[]", "flashcards")


async def _generate_quiz_gemini(content: str, document_id: str) -> List[dict]:
    settings = get_settings()
    max_chars = 12000
    truncated = content[:max_chars] + ("..." if len(content) > max_chars else "")
    system = """You are an expert quiz designer. Create multiple-choice questions from the given material.
Rules: 5-10 MCQs, 4 options each, correctAnswer must be exactly A, B, C, or D, include brief explanation.
Return ONLY a raw JSON array, no markdown: [{"question": "...", "options": ["option1", "option2", "option3", "option4"], "correctAnswer": "B", "explanation": "..."}, ...]"""
    user = f"Create MCQ quiz from this content:\n\n{truncated}\n\nReturn a JSON array of quiz questions."
    loop = asyncio.get_event_loop()

    def _run_once() -> List[dict]:
        text = _gemini_generate_sync(user, system, max_tokens=2500)
        items = _parse_json_array(text or "[]", "quiz")
        for item in items:
            if "correctAnswer" in item:
                item["correct_answer"] = str(item.pop("correctAnswer", "")).strip().upper()
            item.setdefault("options", [])
            item.setdefault("explanation", "")
        return items

    items = await loop.run_in_executor(None, _run_once)
    if not items:
        logger.info("Quiz parse returned empty, retrying once")
        items = await loop.run_in_executor(None, _run_once)
    return items


async def _chat_stream_gemini(messages: List[dict], context: str) -> AsyncGenerator[str, None]:
    system = f"""You are SaiV, a helpful AI learning assistant. Answer based ONLY on this context. If the answer is not in the context, say you're not sure. Be concise and educational.

Context:
{context}"""
    parts = []
    for m in messages:
        role = (m.get("role") or "user").strip().lower()
        content = (m.get("content") or "").strip()
        if role == "user":
            parts.append(f"User: {content}")
        else:
            parts.append(f"Assistant: {content}")
    prompt = "\n\n".join(parts) if parts else "Hello"
    loop = asyncio.get_event_loop()
    chunks = await loop.run_in_executor(
        None,
        lambda: _gemini_stream_sync(prompt, system),
    )
    for chunk in chunks:
        yield chunk


# ---------- OpenAI ----------

async def _generate_flashcards_openai(content: str, document_id: str) -> List[dict]:
    from openai import AsyncOpenAI
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    max_chars = 12000
    truncated = content[:max_chars] + ("..." if len(content) > max_chars else "")
    system = """You are an expert educational content designer. Generate high-quality flashcards from the given learning material.
Rules: 10-15 flashcards, clear questions, concise answers, no duplicates. Return ONLY a valid JSON array: [{"question": "...", "answer": "..."}, ...]"""
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": f"Create flashcards from this content:\n\n{truncated}\n\nReturn a JSON array of flashcards."}],
        temperature=0.5,
        max_tokens=2000,
    )
    text = response.choices[0].message.content or "[]"
    return _parse_json_array(text, "flashcards")


async def _generate_quiz_openai(content: str, document_id: str) -> List[dict]:
    from openai import AsyncOpenAI
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    max_chars = 12000
    truncated = content[:max_chars] + ("..." if len(content) > max_chars else "")
    system = """You are an expert quiz designer. Create MCQs from the material. 5-10 questions, 4 options, correctAnswer A/B/C/D, include explanation. Return ONLY a valid JSON array."""
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": f"Create quiz from this content:\n\n{truncated}\n\nReturn a JSON array of quiz questions."}],
        temperature=0.5,
        max_tokens=2500,
    )
    text = response.choices[0].message.content or "[]"
    items = _parse_json_array(text, "quiz")
    for item in items:
        if "correctAnswer" in item:
            item["correct_answer"] = str(item.pop("correctAnswer", "")).strip().upper()
        item.setdefault("options", [])
        item.setdefault("explanation", "")
    return items


async def _chat_stream_openai(messages: List[dict], context: str) -> AsyncGenerator[str, None]:
    from openai import AsyncOpenAI
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    system_content = f"""You are SaiV. Answer based ONLY on this context. If not in context, say you're not sure. Be concise.

Context:
{context}"""
    api_messages = [{"role": "system", "content": system_content}]
    for m in messages:
        api_messages.append({"role": m["role"], "content": m["content"]})
    stream = await client.chat.completions.create(
        model=settings.openai_model,
        messages=api_messages,
        stream=True,
        temperature=0.3,
        max_tokens=1024,
    )
    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


# ---------- Public API (auto fallback: OpenAI → Gemini) ----------

async def generate_flashcards(content: str, document_id: str) -> List[dict]:
    settings = get_settings()
    provider = (settings.ai_provider or "auto").strip().lower()
    use_gemini_first = provider == "gemini" or (provider == "auto" and not settings.openai_api_key)

    if use_gemini_first and _gemini_available():
        try:
            return await _generate_flashcards_gemini(content, document_id)
        except Exception as e:
            traceback.print_exc()
            logger.warning("Gemini flashcards failed, trying OpenAI", error=str(e))
            if provider == "gemini":
                raise ValueError(f"Gemini failed: {e}") from e

    if settings.openai_api_key:
        try:
            return await _generate_flashcards_openai(content, document_id)
        except Exception as e:
            traceback.print_exc()
            if _gemini_available():
                logger.info("OpenAI failed, falling back to Gemini for flashcards", error=str(e))
                return await _generate_flashcards_gemini(content, document_id)
            _raise_if_quota_error(e)
            raise ValueError(f"AI generation failed: {e}") from e

    if _gemini_available():
        return await _generate_flashcards_gemini(content, document_id)
    raise ValueError(
        "No AI provider configured. Set OPENAI_API_KEY or GEMINI_API_KEY (free at https://aistudio.google.com/apikey) in .env"
    )


async def generate_quiz(content: str, document_id: str) -> List[dict]:
    settings = get_settings()
    provider = (settings.ai_provider or "auto").strip().lower()
    use_gemini_first = provider == "gemini" or (provider == "auto" and not settings.openai_api_key)

    if use_gemini_first and _gemini_available():
        try:
            return await _generate_quiz_gemini(content, document_id)
        except Exception as e:
            traceback.print_exc()
            if provider == "gemini":
                raise ValueError(f"Gemini failed: {e}") from e
            logger.warning("Gemini quiz failed, trying OpenAI", error=str(e))

    if settings.openai_api_key:
        try:
            return await _generate_quiz_openai(content, document_id)
        except Exception as e:
            traceback.print_exc()
            if _gemini_available():
                logger.info("OpenAI failed, falling back to Gemini for quiz", error=str(e))
                return await _generate_quiz_gemini(content, document_id)
            _raise_if_quota_error(e)
            raise ValueError(f"AI generation failed: {e}") from e

    if _gemini_available():
        return await _generate_quiz_gemini(content, document_id)
    raise ValueError(
        "No AI provider configured. Set OPENAI_API_KEY or GEMINI_API_KEY (free at https://aistudio.google.com/apikey) in .env"
    )


async def chat_completion_stream(
    messages: List[dict],
    context: str,
) -> AsyncGenerator[str, None]:
    settings = get_settings()
    provider = (settings.ai_provider or "auto").strip().lower()
    use_gemini_first = provider == "gemini" or (provider == "auto" and not settings.openai_api_key)

    if use_gemini_first and _gemini_available():
        try:
            async for chunk in _chat_stream_gemini(messages, context):
                yield chunk
            return
        except Exception as e:
            traceback.print_exc()
            if provider == "gemini":
                raise ValueError(f"Chat failed: {e}") from e
            logger.warning("Gemini chat failed, trying OpenAI", error=str(e))

    if settings.openai_api_key:
        try:
            async for chunk in _chat_stream_openai(messages, context):
                yield chunk
            return
        except Exception as e:
            traceback.print_exc()
            if _gemini_available():
                logger.info("OpenAI failed, falling back to Gemini for chat", error=str(e))
                async for chunk in _chat_stream_gemini(messages, context):
                    yield chunk
                return
            _raise_if_quota_error(e)
            raise ValueError(f"Chat failed: {e}") from e

    if _gemini_available():
        async for chunk in _chat_stream_gemini(messages, context):
            yield chunk
        return
    raise ValueError(
        "No AI provider configured. Set OPENAI_API_KEY or GEMINI_API_KEY (free at https://aistudio.google.com/apikey) in .env"
    )
