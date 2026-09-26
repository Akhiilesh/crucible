"""Pydantic models for the orders service."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    placed = "placed"
    delivered = "delivered"
    cancelled = "cancelled"
    refunded = "refunded"


class User(BaseModel):
    id: str
    name: str


class Product(BaseModel):
    id: str
    name: str
    price_paise: int  # price in smallest currency unit (paise)
    stock: int


class OrderItem(BaseModel):
    product_id: str
    qty: int = Field(ge=1)


class Order(BaseModel):
    id: str
    user_id: str
    items: list[OrderItem]
    total_paise: int
    status: OrderStatus
    created_at: datetime
    delivered_at: Optional[datetime] = None
    refunded_paise: Optional[int] = None


# ── Request / response shapes ──────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    items: list[OrderItem]


class RefundRequest(BaseModel):
    amount_paise: int


class OrderResponse(BaseModel):
    id: str
    user_id: str
    items: list[OrderItem]
    total_paise: int
    status: OrderStatus
    created_at: datetime
    delivered_at: Optional[datetime] = None
    refunded_paise: Optional[int] = None
