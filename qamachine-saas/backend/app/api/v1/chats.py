from __future__ import annotations

import json
import os
from typing import AsyncGenerator

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db, AsyncSessionLocal
from app.core.security import get_current_user_id
from app.models.chat import Chat, Message
from app.models.run import Run
from app.schemas.chat import (
    ChatOut, ChatCreate, ChatUpdate,
    MessageOut, SendMessageRequest, PaginatedChats,
)
from app.services.machine_runner import MachineRunner

router = APIRouter()

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_ASSIST_MODEL  = "claude-haiku-4-5-20251001"

_ASSIST_SYSTEM = """You are QAmachine AI — an expert QA engineer embedded in QAmachine testing platform.

You are a thinking assistant. You discuss test results, help improve prompts, explain bugs, and can launch new test sessions when explicitly asked.

## Launching a test
When the user clearly asks to run/re-run a test (e.g. "run it again", "test the login", "давай прогоним", "проверь ещё раз"), output this marker on its own line at the very beginning of your response:

[RUN_TEST: <url> | <task description>]

Then continue with a brief message explaining what you're launching.

Rules for RUN_TEST:
- Only use it when user EXPLICITLY asks to start a test. Not for questions, analysis, or prompt help.
- Use the URL the user provided, or the one from the last run if none given.
- Write the task description clearly and specifically (include credentials if user provided them).
- Immediately after the marker, write 1-2 sentences explaining what you're launching.

Examples that SHOULD trigger RUN_TEST:
- "run the test again" → [RUN_TEST: https://site.com | UI/UX audit of the full site]
- "давай ещё раз прогоним" → [RUN_TEST: url | same task as before]
- "test the login form now" → [RUN_TEST: url | Test the login form with email X and password Y]
- "запусти мобильную проверку" → [RUN_TEST: url | Mobile UX check on iPhone 12]

Examples that should NOT trigger RUN_TEST (just answer):
- "why did it fail?" — explain the failure
- "помоги составить промпт" — help write a better prompt
- "what bugs were found?" — summarize bugs
- "how to fix this bug?" — explain the fix

## Your other capabilities:
1. **Analyze results** — interpret bugs, explain their real-world impact, prioritize fixes
2. **Explain failures** — if session crashed or got blocked, explain why and how to fix
3. **Improve prompts** — rewrite vague tasks into clear, specific ones. Format as a ready-to-copy prompt
4. **Suggest next steps** — what mode to use, what to test next, what credentials to add

## Tone:
- Match the user's language (Russian or English)
- Direct, expert, practical. Not robotic.
- Use markdown (bold, lists, code) when it helps.

## Rules:
- NEVER invent bugs not in the report
- NEVER claim capabilities that don't exist (OAuth, CAPTCHA solving, file upload)
- If you don't know, say so honestly
"""

_EVALUATE_SYSTEM = """You are a QA task validator for QAmachine — an autonomous AI QA agent.

Your job: evaluate if the user's test task is clear enough to run successfully.

A good task has:
- A clear objective (what to test: UI, forms, login flow, API, etc.)
- Enough scope (not too vague like "test everything" without more detail)
- Credentials if the site requires login (if it's clearly a private/auth-protected app)
- A reasonable scope (not "test all 500 pages in detail")

Evaluate the task and respond with JSON ONLY (no other text):

If task is READY to run:
{"ready": true, "improved_task": "...slightly improved version of the task if needed, otherwise same..."}

If task needs clarification:
{"ready": false, "questions": "...your clarifying questions or suggestions in the user's language (Russian or English)..."}

Be pragmatic — only ask questions if the task is genuinely ambiguous or will likely fail.
Don't ask unnecessary questions for clear tasks.
If credentials are needed for a private site, ask for them.
Respond in the SAME language the user wrote in (Russian or English).
"""


# ── Mode detection (keyword-based, for plan enforcement) ─────────────────────

_MODE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("network", [
        "network", "сеть", "сетев", "network error", "сетевые ошибки",
        "запросы", "http error", "4xx", "5xx", "network traffic",
        "broken request", "failed request", "network check",
    ]),
    ("api", [
        "api test", "api check", "api endpoint", "тест api", "проверь api",
        "rest api", "апи тест", "тестирование api", "api errors",
        "endpoint", "swagger", "openapi",
    ]),
    ("load_performance", [
        "performance", "load test", "нагрузка", "нагрузочн", "производительност",
        "load time", "page speed", "speed test", "lighthouse",
        "перформанс", "скорость загрузки", "time to interactive",
    ]),
    ("regression", [
        "regression", "регрессия", "регрессионн", "после изменений",
        "after changes", "smoke regression", "что изменилось", "affected areas",
        "затронутые", "smoke after deploy",
    ]),
    ("mobile", [
        "mobile", "мобил", "мобильн", "на телефоне", "на смартфоне",
        "iphone", "android", "pixel ", "galaxy", "айфон", "андроид",
        "mobile ui", "mobile ux", "mobile version",
    ]),
    ("all_flows", [
        "all flows", "все флоу", "all pages", "все страниц",
        "all features", "all functionality", "весь сайт полностью",
        "all scenarios",
    ]),
]


def _detect_task_mode(task: str) -> str | None:
    """Detect likely test mode from task text using keyword matching."""
    import re
    # Check [Mode Name] prefix first (explicit selector)
    _mode_map = {
        "Functional":  "functional",
        "UI/UX Audit": "ui_ux",
        "UI/UX":       "ui_ux",
        "Mobile":      "mobile",
        "Regression":  "regression",
        "Network":     "network",
        "API":         "api",
        "Performance": "load_performance",
        "All Flows":   "all_flows",
    }
    prefix_match = re.match(r"^\[([^\]]+)\]", task.strip())
    if prefix_match:
        label = prefix_match.group(1)
        return _mode_map.get(label, label.lower().replace(" ", "_"))

    # Keyword scan
    task_lower = task.lower()
    for mode, keywords in _MODE_KEYWORDS:
        if any(kw in task_lower for kw in keywords):
            return mode

    return None  # Can't determine — let the engine decide


# ── Chat CRUD ─────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedChats)
async def list_chats(
    page:      int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id:   str = Depends(get_current_user_id),
    db:        AsyncSession = Depends(get_db),
):
    offset  = (page - 1) * page_size
    total_q = await db.execute(
        select(func.count(Chat.id)).where(Chat.user_id == user_id)
    )
    total = total_q.scalar_one()

    result = await db.execute(
        select(Chat)
        .where(Chat.user_id == user_id)
        .options(selectinload(Chat.messages))
        .order_by(Chat.updated_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = result.scalars().all()

    return PaginatedChats(
        items=[ChatOut.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )


@router.post("", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
async def create_chat(
    body:    ChatCreate,
    user_id: str = Depends(get_current_user_id),
    db:      AsyncSession = Depends(get_db),
):
    from app.models.user import User
    from sqlalchemy import select as sel
    u_res = await db.execute(sel(User).where(User.id == user_id))
    user  = u_res.scalar_one()

    if user.is_free:
        count_res = await db.execute(
            select(func.count(Chat.id)).where(Chat.user_id == user_id)
        )
        chat_count = count_res.scalar_one()
        if chat_count >= user.chat_cap:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Free plan allows {user.chat_cap} chat. Upgrade to Pro for unlimited chats.",
            )

    chat = Chat(user_id=user_id, title=body.title)
    chat.messages = []
    db.add(chat)
    await db.flush()
    return chat


@router.get("/{chat_id}", response_model=ChatOut)
async def get_chat(
    chat_id: str,
    user_id: str = Depends(get_current_user_id),
    db:      AsyncSession = Depends(get_db),
):
    chat = await _get_chat_or_404(db, chat_id, user_id)
    return chat


@router.patch("/{chat_id}", response_model=ChatOut)
async def rename_chat(
    chat_id: str,
    body:    ChatUpdate,
    user_id: str = Depends(get_current_user_id),
    db:      AsyncSession = Depends(get_db),
):
    chat = await _get_chat_or_404(db, chat_id, user_id)
    chat.title = body.title
    await db.flush()
    return chat


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: str,
    user_id: str = Depends(get_current_user_id),
    db:      AsyncSession = Depends(get_db),
):
    chat = await _get_chat_or_404(db, chat_id, user_id)
    await db.delete(chat)


# ── Messages ──────────────────────────────────────────────────────────────────

@router.get("/{chat_id}/messages", response_model=list[MessageOut])
async def list_messages(
    chat_id: str,
    user_id: str = Depends(get_current_user_id),
    db:      AsyncSession = Depends(get_db),
):
    await _get_chat_or_404(db, chat_id, user_id)
    result = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at)
    )
    return result.scalars().all()


@router.post("/{chat_id}/messages")
async def send_message(
    chat_id:    str,
    body:       SendMessageRequest,
    background: BackgroundTasks,
    user_id:    str = Depends(get_current_user_id),
    db:         AsyncSession = Depends(get_db),
):
    """
    Create user message → create Run → enqueue in background.
    Returns the created Message and Run immediately.
    """
    chat = await _get_chat_or_404(db, chat_id, user_id)

    # Guard: usage cap + mode restriction
    from app.models.user import User
    from app.core.config import settings
    from sqlalchemy import select as sel
    import re as _re
    u_res = await db.execute(sel(User).where(User.id == user_id))
    user  = u_res.scalar_one()

    if user.usage_credits >= user.usage_cap:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly run limit reached ({user.usage_cap}). Please upgrade your plan.",
        )

    # Free plan: restrict testing modes
    if user.is_free:
        detected_mode = _detect_task_mode(body.task)
        if detected_mode and detected_mode not in settings.FREE_ALLOWED_MODES:
            mode_labels = {
                "network":          "Network testing",
                "api":              "API testing",
                "load_performance": "Performance/Load testing",
                "regression":       "Regression testing",
                "mobile":           "Mobile testing",
                "all_flows":        "All Flows testing",
                "specific_flow":    "Specific Flow testing",
            }
            label = mode_labels.get(detected_mode, detected_mode)
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"{label} is not available on the Free plan. Free plan includes UI/UX and Functional testing only. Upgrade to Pro to unlock all modes.",
            )

    # Resolve target_url: if not provided, reuse URL from the last run in this chat
    target_url = body.target_url
    if not target_url:
        last_run_res = await db.execute(
            select(Run)
            .where(Run.chat_id == chat_id)
            .order_by(Run.created_at.desc())
            .limit(1)
        )
        last_run = last_run_res.scalar_one_or_none()
        if last_run:
            target_url = last_run.target_url
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide a URL for the first message.",
            )

    # Create user message
    user_msg = Message(
        chat_id=chat_id,
        role="user",
        content=f"**URL:** {target_url}\n\n{body.task}" if target_url else body.task,
    )
    db.add(user_msg)
    await db.flush()

    # Create run
    run = Run(
        chat_id=chat_id,
        user_id=user_id,
        target_url=target_url,
        task=body.task,
        status="queued",
        artifacts=[],
    )
    db.add(run)
    await db.flush()

    # Link message to run
    user_msg.run_id = run.id

    # Update chat
    chat.run_count += 1
    chat.status = "running"

    # Increment usage
    user.usage_credits += 1

    await db.flush()

    # Serialize before commit (objects still attached to session)
    from app.schemas.run import RunOut
    response_data = {
        "message": MessageOut.model_validate(user_msg),
        "run":     RunOut.model_validate(run),
    }

    # Commit explicitly so the run exists in DB before background task queries it
    await db.commit()

    # Launch Machine in background (pass plan's allowed modes for engine-level enforcement)
    allowed = settings.FREE_ALLOWED_MODES if user.is_free else None
    background.add_task(MachineRunner().run_async, run.id, target_url, body.task, allowed)

    return response_data


# ── Conversational AI assistant ───────────────────────────────────────────────

class AssistRequest(BaseModel):
    message: str


def _build_run_context(run: Run | None) -> str:
    """Build a text context block from the run's report and summary."""
    if not run:
        return "No test run available yet."

    ctx = f"Run status: {run.status}\n"
    if run.mode:
        ctx += f"Test mode: {run.mode}\n"
    if run.step_count:
        ctx += f"Steps executed: {run.step_count}\n"
    if run.issue_count is not None:
        ctx += f"Issues found: {run.issue_count}\n"
    if run.target_url:
        ctx += f"Tested URL: {run.target_url}\n"
    if run.task:
        ctx += f"Task: {run.task}\n"

    # Include summary (contains failure reason if any)
    if run.summary:
        ctx += f"\nSession summary:\n{run.summary}\n"

    # Include report markdown (first 6000 chars)
    if run.report_path and os.path.exists(run.report_path):
        try:
            with open(run.report_path, encoding="utf-8") as f:
                report_text = f.read(6000)
            ctx += f"\nFull report:\n{report_text}\n"
        except Exception:
            pass

    return ctx


async def _call_claude_json(system: str, user_message: str, api_key: str, max_tokens: int = 512) -> dict:
    """Non-streaming Claude call that returns parsed JSON."""
    headers = {
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "x-api-key": api_key,
    }
    body = {
        "model": _ASSIST_MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user_message}],
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(_ANTHROPIC_URL, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        text = data["content"][0]["text"]
        # Extract JSON from response (may be wrapped in markdown)
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return json.loads(text)


async def _stream_assist(
    messages: list[dict], run_context: str, api_key: str
) -> AsyncGenerator[str, None]:
    system = _ASSIST_SYSTEM + f"\n\n━━ LATEST RUN CONTEXT ━━\n{run_context}\n━━━━━━━━━━━━━━━━━━━━━━━━"
    headers = {
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
        "x-api-key": api_key,
    }
    body = {
        "model": _ASSIST_MODEL,
        "max_tokens": 1500,
        "system": system,
        "messages": messages,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", _ANTHROPIC_URL, headers=headers, json=body) as resp:
            if resp.status_code != 200:
                yield f"data: {json.dumps({'error': 'AI assistant unavailable'})}\n\n"
                return
            async for line in resp.aiter_lines():
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


@router.post("/{chat_id}/assist")
async def assist_chat(
    chat_id: str,
    body:    AssistRequest,
    user_id: str = Depends(get_current_user_id),
    db:      AsyncSession = Depends(get_db),
):
    """Stream a conversational AI response about the latest run in this chat."""
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI assistant not configured.")

    await _get_chat_or_404(db, chat_id, user_id)

    # Fetch last run for context
    run_res = await db.execute(
        select(Run).where(Run.chat_id == chat_id).order_by(Run.created_at.desc()).limit(1)
    )
    last_run = run_res.scalar_one_or_none()
    run_context = _build_run_context(last_run)

    # Fetch recent conversation history (last 12 messages, user/assistant only)
    msgs_res = await db.execute(
        select(Message)
        .where(Message.chat_id == chat_id, Message.role.in_(["user", "assistant"]))
        .order_by(Message.created_at.desc())
        .limit(12)
    )
    history = list(reversed(msgs_res.scalars().all()))

    # Save user message now (before streaming)
    user_msg = Message(chat_id=chat_id, role="user", content=body.message)
    db.add(user_msg)
    await db.commit()

    # Build Anthropic messages array
    anthropic_msgs: list[dict] = []
    for m in history:
        anthropic_msgs.append({"role": m.role, "content": m.content})
    anthropic_msgs.append({"role": "user", "content": body.message})

    async def generate() -> AsyncGenerator[str, None]:
        full_text: list[str] = []
        async for chunk in _stream_assist(anthropic_msgs, run_context, settings.ANTHROPIC_API_KEY):
            yield chunk
            try:
                data = json.loads(chunk.split("data: ", 1)[1])
                if "text" in data:
                    full_text.append(data["text"])
            except Exception:
                pass

        # Save assistant response to DB after streaming completes
        ai_content = "".join(full_text)
        if ai_content:
            async with AsyncSessionLocal() as save_db:
                ai_msg = Message(chat_id=chat_id, role="assistant", content=ai_content)
                save_db.add(ai_msg)
                await save_db.commit()

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Pre-run task evaluation ───────────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    task:       str
    target_url: str = ""


@router.post("/{chat_id}/evaluate")
async def evaluate_task(
    chat_id: str,
    body:    EvaluateRequest,
    user_id: str = Depends(get_current_user_id),
    db:      AsyncSession = Depends(get_db),
):
    """Evaluate if a task is clear enough to run. Returns {ready, questions?, improved_task?}"""
    if not settings.ANTHROPIC_API_KEY:
        return {"ready": True, "improved_task": body.task}

    await _get_chat_or_404(db, chat_id, user_id)

    user_message = f"Task: {body.task}\nURL: {body.target_url or '(not provided)'}"

    try:
        result = await _call_claude_json(_EVALUATE_SYSTEM, user_message, settings.ANTHROPIC_API_KEY)
        return result
    except Exception:
        # On any error, default to ready so the run isn't blocked
        return {"ready": True, "improved_task": body.task}


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_chat_or_404(db: AsyncSession, chat_id: str, user_id: str) -> Chat:
    result = await db.execute(
        select(Chat)
        .where(Chat.id == chat_id, Chat.user_id == user_id)
        .options(selectinload(Chat.messages))
    )
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat
