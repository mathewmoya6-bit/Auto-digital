from pydantic import BaseModel
from typing import Optional


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = "KES"
    active: Optional[bool] = None


class DashboardStats(BaseModel):
    total_users: int
    total_vehicles: int
    total_payments: int
    total_revenue: float
