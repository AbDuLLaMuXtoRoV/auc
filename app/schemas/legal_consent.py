from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConsentDocumentType


class LegalConsentCreate(BaseModel):
    document_type: ConsentDocumentType
    version: str = Field(min_length=1, max_length=40)


class LegalConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_type: ConsentDocumentType
    version: str
    accepted_at: datetime
    ip: str | None
