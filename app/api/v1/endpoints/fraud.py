"""Anti-fraud signal endpointi — FAQAT admin.

Router `/fraud` prefiksini o'zi qo'shadi (router.py), shuning uchun bu yerda
yo'l `/signals/{user_id}` — to'liq yo'l: GET /api/v1/fraud/signals/{user_id}.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import DbSession, current_admin_user
from app.models.user import User
from app.schemas.fraud import FraudSignals
from app.services.fraud_service import FraudService

router = APIRouter()

AdminUser = Annotated[User, Depends(current_admin_user)]


@router.get("/signals/{user_id}", response_model=FraudSignals)
def fraud_signals(user_id: int, _admin: AdminUser, db: DbSession) -> dict:
    """Foydalanuvchi bo'yicha firibgarlik signallarini qaytaradi.

    Admin bo'lmasa `current_admin_user` 403 beradi — signal hisoblanmaydi.
    """
    return FraudService(db).signals_for_user(user_id)
