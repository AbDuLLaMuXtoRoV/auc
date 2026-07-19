import ipaddress

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import settings
from app.core.dependencies import CurrentUser, DbSession
from app.core.webhook import verify_signature
from app.models.payment import Payment, PaymentMethod
from app.schemas.payment import (
    EscrowAction,
    HoldCreate,
    PaymentIntentCreate,
    PaymentMethodCreate,
    PaymentMethodRead,
    PaymentRead,
)
from app.services.payment_service import PaymentService

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    """Mijoz IP'sini qaytaradi — faqat haqiqiy IP bo'lsa.

    audit_log.ip — INET turi. TestClient yoki noto'g'ri host ("testclient")
    kelsa Postgres DataError beradi, shuning uchun validatsiya qilinadi.
    """
    if request.client is None:
        return None
    host = request.client.host
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return None
    return host


@router.post("/methods", response_model=PaymentMethodRead, status_code=status.HTTP_201_CREATED)
def create_method(
    payload: PaymentMethodCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> PaymentMethod:
    payment_method = PaymentMethod(user_id=current_user.id, **payload.model_dump())
    db.add(payment_method)
    db.commit()
    db.refresh(payment_method)
    return payment_method


@router.get("/methods", response_model=list[PaymentMethodRead])
def read_methods(current_user: CurrentUser, db: DbSession) -> list[PaymentMethod]:
    statement = select(PaymentMethod).where(PaymentMethod.user_id == current_user.id)
    return list(db.scalars(statement))


@router.post("/intents", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_payment_intent(
    payload: PaymentIntentCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> Payment:
    return PaymentService(db).create_payment_intent(payload, current_user)


# Mock tasdiqlash endpointi prod/staging'da UMUMAN ro'yxatdan o'tmaydi —
# u yerda OpenAPI'da ham ko'rinmaydi. Servis qatlamida ham tekshiruv bor
# (ikki qatlamli himoya): app/services/payment_service.py:confirm_mock_payment.
if settings.allow_mock_payments:

    @router.post("/{payment_id}/confirm-mock", response_model=PaymentRead)
    def confirm_mock_payment(
        payment_id: int,
        current_user: CurrentUser,
        db: DbSession,
    ) -> Payment:
        return PaymentService(db).confirm_mock_payment(payment_id, current_user)


@router.post("/holds", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def create_hold(
    payload: HoldCreate,
    current_user: CurrentUser,
    db: DbSession,
    request: Request,
) -> Payment:
    return PaymentService(db).create_hold(payload, current_user, ip=_client_ip(request))


@router.post("/{payment_id}/capture", response_model=PaymentRead)
def capture_payment(
    payment_id: int,
    payload: EscrowAction,
    current_user: CurrentUser,
    db: DbSession,
    request: Request,
) -> Payment:
    return PaymentService(db).capture_payment(
        payment_id, payload.idempotency_key, current_user, ip=_client_ip(request)
    )


@router.post("/{payment_id}/release", response_model=PaymentRead)
def release_hold(
    payment_id: int,
    payload: EscrowAction,
    current_user: CurrentUser,
    db: DbSession,
    request: Request,
) -> Payment:
    return PaymentService(db).release_hold(
        payment_id, payload.idempotency_key, current_user, ip=_client_ip(request)
    )


@router.post("/webhooks/psp")
async def psp_webhook(request: Request) -> dict[str, bool]:
    """PSP webhook. Imzosiz qabul qilinmaydi (KRITIK xavfsizlik).

    Imzo XOM BAYT ustida tekshiriladi (parse qilingan JSON emas),
    `hmac.compare_digest` bilan. Imzo noto'g'ri → 401, hech qanday yon
    effektsiz. Autentifikatsiyadan ozod, lekin imzodan ozod EMAS.
    """
    raw_body = await request.body()
    signature = request.headers.get("x-signature", "")
    if not verify_signature(raw_body, signature, settings.psp_webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")
    # TODO (Faza D davomi): hodisani parse qilib, PSP holatidan payment'ni
    # yangilash (provider_event_id bo'yicha idempotent). Hozircha imzo
    # tekshiruvi — eng kritik qism — o'rnatildi.
    return {"ok": True}


@router.get("/orders/{order_id}", response_model=PaymentRead)
def get_payment_by_order(
    order_id: int,
    current_user: CurrentUser,
    db: DbSession,
) -> Payment:
    return PaymentService(db).get_payment_by_order(order_id, current_user)
