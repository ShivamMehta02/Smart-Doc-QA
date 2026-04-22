from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import openai
from openai import AsyncOpenAI
from app.core.config import settings
from app.core.exceptions import OpenAIUnavailableError, OpenAIKeyMissingError
from app.core.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a precise document assistant.

Rules (STRICTLY follow these):
1. Answer ONLY using the provided context below.
2. Do NOT use any external knowledge or make assumptions.
3. If the answer is not in the context, respond with exactly: "NOT_IN_DOCUMENT"
4. Be concise. Cite the page number when possible.
5. Never fabricate citations or page numbers."""


def _get_client() -> AsyncOpenAI:
    if not settings.OPENAI_API_KEY:
        raise OpenAIKeyMissingError()
    return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


def _build_prompt(question: str, context_chunks: List[dict], history: Optional[List[dict]] = None) -> List[dict]:
    """Build the message list for the OpenAI Chat API."""
    context_text = "\n\n---\n\n".join(
        f"[Page {c.get('page', '?')}]: {c['text']}" for c in context_chunks
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history for chat mode
    if history:
        for msg in history[-6:]:  # Last 3 turns (6 messages)
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({
        "role": "user",
        "content": f"Context:\n{context_text}\n\nQuestion: {question}"
    })

    return messages


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError)),
    reraise=True,
)
async def call_llm(question: str, context_chunks: List[dict], history: Optional[List[dict]] = None) -> dict:
    """
    Call OpenAI with retry logic.
    Returns {"answer": str, "raw_response": str}
    
    Retry strategy: 3 attempts, exponential backoff 2–10s.
    Catches rate limits and connection errors only (not auth errors).
    """
    try:
        client = _get_client()
        messages = _build_prompt(question, context_chunks, history)

        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=settings.OPENAI_MAX_TOKENS,
            temperature=settings.OPENAI_TEMPERATURE,
        )

        answer = response.choices[0].message.content.strip()
        logger.info("llm_response_received", tokens_used=response.usage.total_tokens)
        return {"answer": answer, "raw_response": answer}

    except OpenAIKeyMissingError:
        raise
    except (openai.RateLimitError, openai.APIConnectionError):
        logger.warning("llm_retry_triggered")
        raise
    except openai.AuthenticationError:
        logger.error("llm_auth_failed")
        raise OpenAIUnavailableError()
    except Exception as e:
        logger.error("llm_call_failed", error=str(e))
        raise OpenAIUnavailableError()
