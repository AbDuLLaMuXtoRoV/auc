from abc import ABC, abstractmethod
from decimal import Decimal
from uuid import uuid4

from app.models.enums import PaymentStatus


class PaymentProviderResult:
    def __init__(self, provider_payment_id: str, status: PaymentStatus) -> None:
        self.provider_payment_id = provider_payment_id
        self.status = status


class BasePaymentProvider(ABC):
    provider_name: str

    @abstractmethod
    def create_payment(self, *, amount: Decimal, currency: str) -> PaymentProviderResult:
        raise NotImplementedError

    @abstractmethod
    def confirm_payment(self, *, provider_payment_id: str) -> PaymentProviderResult:
        raise NotImplementedError


class MockPaymentProvider(BasePaymentProvider):
    provider_name = "mock"

    def create_payment(self, *, amount: Decimal, currency: str) -> PaymentProviderResult:
        # TODO: Replace with Uzcard/Humo, Payme/Click, or another provider adapter.
        return PaymentProviderResult(
            provider_payment_id=f"mock_{uuid4().hex}",
            status=PaymentStatus.PENDING,
        )

    def confirm_payment(self, *, provider_payment_id: str) -> PaymentProviderResult:
        return PaymentProviderResult(
            provider_payment_id=provider_payment_id,
            status=PaymentStatus.PAID,
        )


def get_payment_provider(provider: str) -> BasePaymentProvider:
    if provider == MockPaymentProvider.provider_name:
        return MockPaymentProvider()
    # TODO: Register real providers through configuration or dependency injection.
    return MockPaymentProvider()
