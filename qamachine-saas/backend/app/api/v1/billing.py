from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone

import httpx
import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.analytics import Payment
from app.models.run import Subscription
from app.models.user import User

NOWPAYMENTS_BASE = "https://api.nowpayments.io/v1"
PLAN_PRICES = {"pro": 29, "team": 79}

router = APIRouter()

PLAN_TO_PRICE: dict[str, str] = {
    "pro":  settings.STRIPE_PRICE_PRO,
    "team": settings.STRIPE_PRICE_TEAM,
}


def _require_stripe() -> None:
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=501,
            detail="Stripe billing not configured. Set STRIPE_SECRET_KEY in .env.",
        )
    stripe.api_key = settings.STRIPE_SECRET_KEY


# ── Subscription (current plan) ───────────────────────────────────────────────

@router.get("/subscription")
async def get_subscription(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    sub = result.scalar_one_or_none()
    if not sub:
        user_res = await db.execute(select(User).where(User.id == user_id))
        user = user_res.scalar_one_or_none()
        user_plan = user.plan if user else "free"
        return {
            "id":                      f"{user_plan}_{user_id}",
            "user_id":                 user_id,
            "plan":                    user_plan,
            "status":                  "active",
            "current_period_start":    None,
            "current_period_end":      None,
            "cancel_at_period_end":    False,
            "stripe_subscription_id":  None,
        }
    return sub


# ── Invoices ──────────────────────────────────────────────────────────────────

@router.get("/invoices")
async def get_invoices(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not settings.STRIPE_SECRET_KEY:
        return []
    stripe.api_key = settings.STRIPE_SECRET_KEY

    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    sub = result.scalar_one_or_none()
    if not sub or not sub.stripe_customer_id:
        return []

    try:
        invoices = stripe.Invoice.list(customer=sub.stripe_customer_id, limit=20)
        return [
            {
                "id":          inv.id,
                "amount":      inv.amount_paid,
                "currency":    inv.currency,
                "status":      inv.status,
                "description": inv.lines.data[0].description if inv.lines.data else "Subscription",
                "date":        datetime.fromtimestamp(inv.created, tz=timezone.utc).isoformat(),
                "invoice_url": inv.hosted_invoice_url,
            }
            for inv in invoices.data
        ]
    except Exception:
        return []


# ── Checkout ──────────────────────────────────────────────────────────────────

@router.post("/checkout")
async def create_checkout_session(
    body: dict,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    _require_stripe()

    plan_id = body.get("plan_id", "")
    price_id = PLAN_TO_PRICE.get(plan_id)
    if not price_id:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown plan: {plan_id!r}. Expected 'pro' or 'team'.",
        )

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get or lazily create Stripe customer
    sub_result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    sub = sub_result.scalar_one_or_none()
    customer_id = sub.stripe_customer_id if sub else None

    if not customer_id:
        customer = stripe.Customer.create(
            email=user.email,
            name=user.name or user.email,
            metadata={"user_id": user_id},
        )
        customer_id = customer.id
        if sub:
            sub.stripe_customer_id = customer_id
        else:
            sub = Subscription(
                user_id=user_id,
                plan="free",
                status="active",
                stripe_customer_id=customer_id,
            )
            db.add(sub)
        await db.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=f"{settings.FRONTEND_URL}/billing?success=1",
        cancel_url=f"{settings.FRONTEND_URL}/billing?canceled=1",
        metadata={"user_id": user_id, "plan": plan_id},
        subscription_data={"metadata": {"user_id": user_id, "plan": plan_id}},
    )

    return {"url": session.url}


# ── Customer portal ───────────────────────────────────────────────────────────

@router.post("/portal")
async def create_portal_session(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    _require_stripe()

    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    sub = result.scalar_one_or_none()
    if not sub or not sub.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No Stripe subscription found. Please subscribe first.",
        )

    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=f"{settings.FRONTEND_URL}/billing",
    )
    return {"url": session.url}


# ── Webhook (no JWT — Stripe signature) ──────────────────────────────────────

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="stripe-signature"),
    db: AsyncSession = Depends(get_db),
):
    if not settings.STRIPE_SECRET_KEY or not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=501, detail="Stripe not configured.")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    body = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            body, stripe_signature or "", settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature.")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    etype = event["type"]
    data  = event["data"]["object"]

    if etype == "checkout.session.completed":
        await _handle_checkout_completed(db, data)
    elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
        await _handle_subscription_change(db, data, deleted=etype.endswith("deleted"))
    elif etype == "invoice.payment_succeeded":
        await _handle_invoice_paid(db, data)

    return {"ok": True}


# ── Webhook helpers ───────────────────────────────────────────────────────────

async def _handle_checkout_completed(db: AsyncSession, session: dict) -> None:
    user_id            = (session.get("metadata") or {}).get("user_id")
    plan               = (session.get("metadata") or {}).get("plan", "pro")
    stripe_sub_id      = session.get("subscription")
    stripe_customer_id = session.get("customer")
    amount             = session.get("amount_total", 0)

    if not user_id:
        return

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if user:
        user.plan = plan

    sub_res = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    sub = sub_res.scalar_one_or_none()
    if sub:
        sub.plan   = plan
        sub.status = "active"
        if stripe_sub_id:
            sub.stripe_subscription_id = stripe_sub_id
        if stripe_customer_id:
            sub.stripe_customer_id = stripe_customer_id
    else:
        db.add(Subscription(
            user_id=user_id,
            plan=plan,
            status="active",
            stripe_subscription_id=stripe_sub_id,
            stripe_customer_id=stripe_customer_id,
        ))

    # Record payment (dedup via checkout_{stripe_sub_id})
    if stripe_sub_id and amount > 0:
        dedup_key = f"checkout_{stripe_sub_id}"
        existing = await db.execute(select(Payment).where(Payment.stripe_payment_id == dedup_key))
        if not existing.scalar_one_or_none():
            db.add(Payment(
                user_id=user_id,
                amount_cents=amount,
                currency=session.get("currency", "usd"),
                plan=plan,
                stripe_payment_id=dedup_key,
            ))

    await db.commit()


async def _handle_subscription_change(db: AsyncSession, stripe_sub: dict, deleted: bool) -> None:
    stripe_sub_id = stripe_sub["id"]
    res = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    sub = res.scalar_one_or_none()
    if not sub:
        return

    if deleted:
        sub.status = "canceled"
        sub.plan   = "free"
        user_res = await db.execute(select(User).where(User.id == sub.user_id))
        user = user_res.scalar_one_or_none()
        if user:
            user.plan = "free"
    else:
        sub.status = stripe_sub.get("status", sub.status)
        ps = stripe_sub.get("current_period_start")
        pe = stripe_sub.get("current_period_end")
        if ps:
            sub.current_period_start = datetime.fromtimestamp(ps, tz=timezone.utc)
        if pe:
            sub.current_period_end = datetime.fromtimestamp(pe, tz=timezone.utc)
        sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
        plan_from_meta = (stripe_sub.get("metadata") or {}).get("plan")
        if plan_from_meta:
            sub.plan = plan_from_meta

    await db.commit()


# ── NOWPayments (crypto) checkout ────────────────────────────────────────────

@router.post("/checkout/crypto")
async def create_crypto_checkout(
    body: dict,
    user_id: str = Depends(get_current_user_id),
):
    if not settings.NOWPAYMENTS_API_KEY:
        raise HTTPException(status_code=501, detail="Crypto payments not configured.")

    plan_id = body.get("plan_id", "")
    price = PLAN_PRICES.get(plan_id)
    if not price:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan_id!r}")

    order_id = f"{user_id}__{plan_id}__{int(time.time())}"
    callback_url = f"{settings.FRONTEND_URL.rstrip('/')}/api/v1/billing/webhook/crypto"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{NOWPAYMENTS_BASE}/invoice",
            headers={"x-api-key": settings.NOWPAYMENTS_API_KEY, "Content-Type": "application/json"},
            json={
                "price_amount": price,
                "price_currency": "usd",
                "order_id": order_id,
                "order_description": f"QAmachine {plan_id.title()} Plan — 30 days",
                "ipn_callback_url": callback_url,
                "success_url": f"{settings.FRONTEND_URL}/billing?success=1",
                "cancel_url": f"{settings.FRONTEND_URL}/billing?canceled=1",
                "is_fixed_rate": False,
                "is_fee_paid_by_user": False,
            },
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to create crypto invoice.")

    return {"url": resp.json()["invoice_url"]}


# ── NOWPayments IPN webhook ───────────────────────────────────────────────────

@router.post("/webhook/crypto")
async def nowpayments_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body_bytes = await request.body()
    sig = request.headers.get("x-nowpayments-sig", "")

    if settings.NOWPAYMENTS_IPN_SECRET and sig:
        body_dict = json.loads(body_bytes)
        sorted_body = json.dumps(body_dict, sort_keys=True, separators=(",", ":"))
        expected = hmac.new(
            settings.NOWPAYMENTS_IPN_SECRET.encode(),
            sorted_body.encode(),
            hashlib.sha512,
        ).hexdigest()
        if not hmac.compare_digest(expected, sig):
            raise HTTPException(status_code=400, detail="Invalid IPN signature.")

    data = json.loads(body_bytes)
    if data.get("payment_status") != "finished":
        return {"ok": True}

    order_id = data.get("order_id", "")
    parts = order_id.split("__")
    if len(parts) < 2:
        return {"ok": True}

    user_id, plan_id = parts[0], parts[1]
    await _activate_crypto_plan(db, user_id, plan_id, data)
    return {"ok": True}


async def _activate_crypto_plan(db: AsyncSession, user_id: str, plan_id: str, data: dict) -> None:
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        return

    user.plan = plan_id
    now = datetime.now(timezone.utc)
    period_end = now + timedelta(days=30)

    sub_res = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    sub = sub_res.scalar_one_or_none()
    if sub:
        sub.plan = plan_id
        sub.status = "active"
        sub.current_period_start = now
        sub.current_period_end = period_end
    else:
        db.add(Subscription(
            user_id=user_id, plan=plan_id, status="active",
            current_period_start=now, current_period_end=period_end,
        ))

    payment_id = str(data.get("payment_id", ""))
    dedup_key = f"np_{payment_id}"
    existing = await db.execute(select(Payment).where(Payment.stripe_payment_id == dedup_key))
    if not existing.scalar_one_or_none():
        amount_cents = int(float(data.get("price_amount", 0)) * 100)
        db.add(Payment(
            user_id=user_id, amount_cents=amount_cents,
            currency="usd", plan=plan_id, stripe_payment_id=dedup_key,
        ))

    await db.commit()


async def _handle_invoice_paid(db: AsyncSession, invoice: dict) -> None:
    stripe_invoice_id  = invoice.get("id")
    stripe_customer_id = invoice.get("customer")
    amount_paid        = invoice.get("amount_paid", 0)

    if not stripe_invoice_id or not stripe_customer_id or not amount_paid:
        return

    existing = await db.execute(select(Payment).where(Payment.stripe_payment_id == stripe_invoice_id))
    if existing.scalar_one_or_none():
        return

    res = await db.execute(
        select(Subscription).where(Subscription.stripe_customer_id == stripe_customer_id)
    )
    sub = res.scalar_one_or_none()
    if not sub:
        return

    db.add(Payment(
        user_id=sub.user_id,
        amount_cents=amount_paid,
        currency=invoice.get("currency", "usd"),
        plan=sub.plan,
        stripe_payment_id=stripe_invoice_id,
    ))
    await db.commit()


# ── Dodo Payments (card) checkout ─────────────────────────────────────────────

@router.post("/checkout/card")
async def create_card_checkout(
    body: dict,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if not settings.DODO_API_KEY:
        raise HTTPException(status_code=501, detail="Card payments not configured.")

    plan_id = body.get("plan_id", "")
    product_id = {
        "pro":  settings.DODO_PRODUCT_PRO,
        "team": settings.DODO_PRODUCT_TEAM,
    }.get(plan_id)
    if not product_id:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {plan_id!r}")

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    dodo_base = f"https://{settings.DODO_ENV}.dodopayments.com"
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{dodo_base}/subscriptions",
            headers={
                "Authorization": f"Bearer {settings.DODO_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "billing": {
                    "city": "N/A",
                    "country": "US",
                    "state": "N/A",
                    "street": "N/A",
                    "zipcode": "00000",
                },
                "customer": {
                    "create_new_customer": True,
                    "email": user.email,
                    "name": user.name or user.email,
                },
                "payment_link": True,
                "product_id": product_id,
                "quantity": 1,
                "metadata": {"user_id": user_id, "plan": plan_id},
                "return_url": f"{settings.FRONTEND_URL}/billing?success=1",
            },
        )

    if resp.status_code not in (200, 201):
        import logging
        logging.getLogger("billing").error(
            "Dodo card checkout failed: status=%s body=%s", resp.status_code, resp.text
        )
        raise HTTPException(status_code=502, detail=f"Dodo error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    url = data.get("payment_link") or data.get("checkout_url") or data.get("url")
    if not url:
        raise HTTPException(status_code=502, detail="No checkout URL returned.")
    return {"url": url}


# ── Dodo Payments webhook ─────────────────────────────────────────────────────

@router.post("/webhook/dodo")
async def dodo_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body_bytes = await request.body()
    data = json.loads(body_bytes)

    # Verify signature if secret is configured
    if settings.DODO_WEBHOOK_SECRET:
        sig = request.headers.get("webhook-signature", "")
        timestamp = request.headers.get("webhook-timestamp", "")
        signed_content = f"{timestamp}.{body_bytes.decode()}"
        expected = hmac.new(
            settings.DODO_WEBHOOK_SECRET.encode(),
            signed_content.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, sig.split(",")[-1] if "," in sig else sig):
            raise HTTPException(status_code=400, detail="Invalid webhook signature.")

    event_type = data.get("type") or data.get("event_type", "")
    payload    = data.get("data") or data

    if event_type in ("subscription.active", "payment.succeeded", "subscription.renewed"):
        await _handle_dodo_payment(db, payload, event_type)

    return {"ok": True}


async def _handle_dodo_payment(db: AsyncSession, payload: dict, event_type: str) -> None:
    metadata  = payload.get("metadata") or {}
    user_id   = metadata.get("user_id")
    plan_id   = metadata.get("plan")
    payment_id = str(payload.get("subscription_id") or payload.get("payment_id") or "")

    if not user_id or not plan_id:
        return

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        return

    user.plan = plan_id
    now        = datetime.now(timezone.utc)
    period_end = now + timedelta(days=31)

    sub_res = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    sub = sub_res.scalar_one_or_none()
    if sub:
        sub.plan   = plan_id
        sub.status = "active"
        sub.current_period_start = now
        sub.current_period_end   = period_end
    else:
        db.add(Subscription(
            user_id=user_id, plan=plan_id, status="active",
            current_period_start=now, current_period_end=period_end,
        ))

    dedup_key = f"dodo_{payment_id}"
    existing = await db.execute(select(Payment).where(Payment.stripe_payment_id == dedup_key))
    if not existing.scalar_one_or_none() and payment_id:
        amount_cents = int(PLAN_PRICES.get(plan_id, 0) * 100)
        db.add(Payment(
            user_id=user_id, amount_cents=amount_cents,
            currency="usd", plan=plan_id, stripe_payment_id=dedup_key,
        ))

    await db.commit()
