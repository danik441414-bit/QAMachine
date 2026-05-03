from __future__ import annotations

import json
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.user import User

router = APIRouter()

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_MODEL = "claude-haiku-4-5-20251001"

_SYSTEM = """You are QA Mentor — a senior QA engineer and educator with 15+ years of experience.
Your job is to teach QA engineering using the most effective methods:
- Socratic questioning: ask the student questions to guide them to the answer
- Concrete examples: always illustrate with real-world scenarios
- Practice tasks: offer small exercises after explaining concepts
- Incremental complexity: start simple, add layers
- Connect theory to tools: link concepts to Playwright, Selenium, Postman, etc.

You specialize in:
- Manual testing (test cases, bug reports, test plans, checklists)
- Test automation (Playwright, Selenium, pytest, CI/CD)
- API testing (REST, Postman, HTTP methods, status codes)
- Performance testing (JMeter, k6, Web Vitals, load testing)
- Test design techniques (equivalence partitioning, boundary values, pairwise)
- QA processes (Agile/Scrum QA, regression, smoke, exploratory testing)
- Bug reporting (severity, priority, steps to reproduce, good vs bad reports)

Teaching style:
- Respond in the language the student writes in (Russian or English)
- Keep answers concise but complete — use bullet points and code blocks
- After each explanation, offer: "Want a practice exercise?" or "Shall we go deeper?"
- Praise good questions and correct mistakes gently
- Use analogies to explain complex concepts

You are inside QAmachine — an AI-powered QA platform. Students may ask about QAmachine features too."""


class TutorMessage(BaseModel):
    role: str
    content: str


class TutorChatRequest(BaseModel):
    messages: list[TutorMessage]


async def _stream_anthropic(
    messages: list[dict], api_key: str
) -> AsyncGenerator[str, None]:
    headers = {
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "x-api-key": api_key,
    }
    body = {
        "model": _MODEL,
        "max_tokens": 1500,
        "system": _SYSTEM,
        "messages": messages,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream(
            "POST", _ANTHROPIC_URL, headers=headers, json=body
        ) as response:
            if response.status_code != 200:
                error_body = await response.aread()
                yield f"data: {json.dumps({'error': f'API error {response.status_code}'})}\n\n"
                return
            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[6:]
                if raw.strip() == "[DONE]":
                    break
                try:
                    event = json.loads(raw)
                    if event.get("type") == "content_block_delta":
                        text = event.get("delta", {}).get("text", "")
                        if text:
                            yield f"data: {json.dumps({'text': text})}\n\n"
                except (json.JSONDecodeError, KeyError):
                    continue


@router.post("/chat")
async def tutor_chat(
    body:    TutorChatRequest,
    user_id: str = Depends(get_current_user_id),
    db:      AsyncSession = Depends(get_db),
):
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tutor is not available — ANTHROPIC_API_KEY not configured.",
        )

    res  = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one()

    if user.tutor_credits >= user.tutor_cap:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly tutor message limit reached ({user.tutor_cap}). Upgrade to Pro for unlimited access.",
        )

    # Increment before streaming so it's always tracked even if client disconnects
    user.tutor_credits += 1
    await db.commit()

    messages = [{"role": m.role, "content": m.content} for m in body.messages]

    async def generate() -> AsyncGenerator[str, None]:
        async for chunk in _stream_anthropic(messages, settings.ANTHROPIC_API_KEY):
            yield chunk
        remaining = max(0, user.tutor_cap - user.tutor_credits)
        yield f"data: {json.dumps({'done': True, 'tutor_credits': user.tutor_credits, 'tutor_cap': user.tutor_cap, 'remaining': remaining})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/usage")
async def tutor_usage(
    user_id: str = Depends(get_current_user_id),
    db:      AsyncSession = Depends(get_db),
):
    res  = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one()
    return {
        "tutor_credits": user.tutor_credits,
        "tutor_cap":     user.tutor_cap,
        "remaining":     max(0, user.tutor_cap - user.tutor_credits),
        "is_limited":    user.is_free,
    }
