from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import UserRole


class UserRoleUpdate(BaseModel):
    role: UserRole


class AdminStatsRead(BaseModel):
    total_users: int
    total_active_auctions: int
    total_completed_orders: int
    total_sales_amount: Decimal
