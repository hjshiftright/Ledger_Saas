"""Chat API — conversational AI assistant with live financial context.

POST /api/v1/chat
    Body:    { message, history?, provider_id? }
    Returns: { reply, provider }

The endpoint:
  1. Resolves the user's configured LLM provider (or env default).
  2. Classifies the question via keyword matching.
  3. Fetches the relevant financial data directly from the DB.
  4. Injects that data into a grounding system prompt.
  5. Calls the LLM with the full conversation history.
  6. Returns a concise, data-backed natural-language reply.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from fastapi import HTTPException
from fastapi.routing import APIRouter
from pydantic import BaseModel

from api.deps import CurrentUser, DBSession, SettingsDep

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)


# ── Schemas ───────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str      # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    provider_id: str | None = None


# ── Keyword → data category routing ──────────────────────────────────────────

_CATEGORIES: dict[str, list[str]] = {
    "goals":   ["goal", "goals", "target", "saving for", "working towards", "dream", "emergency fund"],
    "budgets": ["budget", "budgets", "limit", "overspend", "over budget", "allowance"],
    "income":  ["income", "salary", "earn", "revenue", "pay", "credit"],
    "expense": ["expense", "spend", "spending", "spent", "category", "categories", "debit"],
    "assets":  ["asset", "assets", "liability", "liabilities", "debt", "loan", "emi",
                "balance sheet", "owe", "worth", "property", "mutual fund", "equity"],
    "trends":  ["trend", "monthly", "month", "this month", "last month", "over time",
                "last year", "history", "pattern"],
    "fire":    ["fire", "retire", "retirement", "financial independence", "runway",
                "corpus", "fi number", "passive income", "how long"],
    "tax":     ["tax", "80c", "80d", "section", "deduction", "hra", "nps", "elss"],
}


def _classify(msg: str) -> set[str]:
    m = msg.lower()
    return {cat for cat, words in _CATEGORIES.items() if any(w in m for w in words)}


# ── Context fetch ─────────────────────────────────────────────────────────────

def _fetch_context(user_id: str, session: Any, categories: set[str]) -> dict[str, Any]:
    """Pull the minimal set of financial data needed to answer the question."""
    from api.routers.reports import (  # noqa: PLC0415
        reports_summary,
        income_expense,
        expense_categories,
        balance_sheet,
        monthly_trend,
        dashboard_life_insights,
        dashboard_tax,
    )
    from api.routers.goals import list_goals      # noqa: PLC0415
    from api.routers.budgets import list_budgets  # noqa: PLC0415

    today = date.today()
    ctx: dict[str, Any] = {}

    # Summary is always included — net worth, period I&E, top expenses
    try:
        ctx["financial_summary"] = reports_summary(
            user_id=user_id, session=session,
            as_of=today, from_date=None, to_date=None,
        )
    except Exception as exc:
        logger.warning("chat ctx: summary failed: %s", exc)

    if "goals" in categories:
        try:
            raw = list_goals(user=user_id, session=session)
            ctx["goals"] = [g.model_dump() for g in raw]
        except Exception as exc:
            logger.warning("chat ctx: goals failed: %s", exc)

    if "budgets" in categories:
        try:
            raw = list_budgets(user=user_id, session=session)
            ctx["budgets"] = [b.model_dump() for b in raw]
        except Exception as exc:
            logger.warning("chat ctx: budgets failed: %s", exc)

    if {"expense", "income"} & categories:
        try:
            ctx["income_expense"] = income_expense(
                user_id=user_id, session=session, from_date=None, to_date=None,
            )
            ctx["expense_breakdown"] = expense_categories(
                user_id=user_id, session=session, from_date=None, to_date=None,
            )
        except Exception as exc:
            logger.warning("chat ctx: income/expense failed: %s", exc)

    if "assets" in categories:
        try:
            ctx["balance_sheet"] = balance_sheet(
                user_id=user_id, session=session, as_of=None,
            )
        except Exception as exc:
            logger.warning("chat ctx: balance-sheet failed: %s", exc)

    if "trends" in categories:
        try:
            ctx["monthly_trend"] = monthly_trend(
                user_id=user_id, session=session, months=12,
            )
        except Exception as exc:
            logger.warning("chat ctx: trend failed: %s", exc)

    if "fire" in categories:
        try:
            ctx["life_insights"] = dashboard_life_insights(
                user_id=user_id, session=session, months=12,
            )
        except Exception as exc:
            logger.warning("chat ctx: life-insights failed: %s", exc)

    if "tax" in categories:
        try:
            ctx["tax_optimization"] = dashboard_tax(
                user_id=user_id, session=session,
            )
        except Exception as exc:
            logger.warning("chat ctx: tax failed: %s", exc)

    return ctx


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are Finny — a personal finance assistant embedded in the Ledger app.

You have access to the user's actual financial data (provided in JSON below). \
Always use it to give precise, data-backed answers with exact numbers.

Rules:
- Keep replies short and conversational (3-5 sentences) unless the user asks for detail.
- Always quote real numbers from the data (e.g. "Your net worth is ₹12.4 L").
- Use Indian currency (₹). For large amounts use lakhs/crores shorthand when helpful \
  (e.g. ₹2.3 L, ₹1.1 Cr).
- If the user asks something the data doesn't cover, be honest and say so.
- Write in warm, friendly prose — like a knowledgeable friend, not a report.
- Use a numbered or bulleted list only when you genuinely have multiple items to enumerate.
- Never mention JSON, databases, or internal systems.
- Today: {today}

User's live financial data:
{context}
"""


# ── LLM call router ───────────────────────────────────────────────────────────

def _call_llm(provider_name: str, provider: Any, system: str,
              messages: list[dict]) -> str:
    """Call the appropriate LLM SDK and return the reply text."""
    if provider_name == "gemini":
        from google import genai        # noqa: PLC0415
        from google.genai import types  # noqa: PLC0415

        # Gemini SDK doesn't support message-level roles in the same way;
        # flatten history into a readable transcript prepended to the message.
        history_lines = ""
        for m in messages[:-1][-8:]:  # cap at last 4 turns (8 messages)
            label = "You" if m["role"] == "user" else "Ledger AI"
            history_lines += f"{label}: {m['content']}\n"

        prompt = history_lines + f"You: {messages[-1]['content']}" if history_lines else messages[-1]["content"]

        client = genai.Client(api_key=provider._api_key)
        resp = client.models.generate_content(
            model=provider._text_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=2048,
            ),
        )
        if not resp.candidates or not resp.candidates[0].content or not resp.candidates[0].content.parts:
            return ""
        return "".join(p.text for p in resp.candidates[0].content.parts if p.text)

    if provider_name == "openai":
        from openai import OpenAI  # noqa: PLC0415
        client = OpenAI(api_key=provider._api_key)
        resp = client.chat.completions.create(
            model=provider._text_model or "gpt-4o-mini",
            messages=[{"role": "system", "content": system}] + messages,
            max_tokens=700,
            temperature=0.15,
        )
        return resp.choices[0].message.content

    if provider_name == "anthropic":
        import anthropic  # noqa: PLC0415
        client = anthropic.Anthropic(api_key=provider._api_key)
        resp = client.messages.create(
            model=provider._text_model or "claude-3-haiku-20240307",
            max_tokens=700,
            system=system,
            messages=messages,
        )
        return resp.content[0].text

    raise ValueError(f"Unsupported provider: {provider_name}")


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("", summary="Conversational AI — answers financial questions with live data")
def chat(
    body: ChatRequest,
    user_id: CurrentUser,
    session: DBSession,
    settings: SettingsDep,
):
    # 1. Resolve LLM provider
    try:
        from api.routers.llm import _resolve_provider  # noqa: PLC0415
        from db.models.system import LlmProvider       # noqa: PLC0415
        from sqlalchemy import select                   # noqa: PLC0415

        pid = body.provider_id
        if pid is None:
            db_prov = session.execute(
                select(LlmProvider)
                .where(
                    LlmProvider.user_id == user_id,
                    LlmProvider.is_active == True,  # noqa: E712
                )
                .order_by(LlmProvider.is_default.desc())
                .limit(1)
            ).scalar_one_or_none()
            if db_prov:
                pid = db_prov.provider_id

        provider_name, provider = _resolve_provider(user_id, pid, settings, session)

    except HTTPException:
        return {
            "reply": (
                "I don't have an LLM provider set up yet. "
                "Go to Settings → LLM Providers, add your API key, and I'll be ready to help."
            ),
            "provider": None,
        }

    # 2. Classify question & fetch grounding data
    categories = _classify(body.message)
    ctx_data   = _fetch_context(user_id, session, categories)
    ctx_json   = json.dumps(ctx_data, indent=2, default=str)

    system = _SYSTEM_PROMPT.format(
        today=date.today().strftime("%d %B %Y"),
        context=ctx_json,
    )

    # 3. Build message list for LLM
    messages = [{"role": m.role, "content": m.content} for m in body.history]
    messages.append({"role": "user", "content": body.message})

    # 4. Call LLM and return
    try:
        reply = _call_llm(provider_name, provider, system, messages)
        return {"reply": reply, "provider": provider_name}

    except Exception as exc:       # noqa: BLE001
        logger.error("chat: LLM call failed: %s", exc, exc_info=True)
        return {
            "reply": f"The AI hit a snag: {exc}. Try again in a moment.",
            "provider": provider_name,
        }
