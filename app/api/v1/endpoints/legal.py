from fastapi import APIRouter, Request, status

from app.core.dependencies import CurrentUser, DbSession
from app.core.request_meta import client_ip
from app.models.legal_consent import LegalConsent
from app.schemas.legal_consent import LegalConsentCreate, LegalConsentRead
from app.services.legal_consent_service import LegalConsentService

router = APIRouter()


@router.post("/consent", response_model=LegalConsentRead, status_code=status.HTTP_201_CREATED)
def record_consent(
    payload: LegalConsentCreate,
    current_user: CurrentUser,
    db: DbSession,
    request: Request,
) -> LegalConsent:
    """Huquqiy hujjatga rozilikni yozib qo'yadi. IP audit uchun saqlanadi."""
    return LegalConsentService(db).record(
        current_user,
        payload.document_type,
        payload.version,
        ip=client_ip(request),
    )


@router.get("/consents", response_model=list[LegalConsentRead])
def list_consents(
    current_user: CurrentUser,
    db: DbSession,
) -> list[LegalConsent]:
    """Mening qabullarim."""
    return LegalConsentService(db).list_mine(current_user)
