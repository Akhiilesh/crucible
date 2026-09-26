"""In-memory store for the orders service.

All state lives in module-level dicts so tests can call reset() to get a
clean slate between runs.
"""
from __future__ import annotations

import copy
from typing import Optional

from app.models import Order, Product, User

# ── Seed data (restored on every reset) ────────────────────────────────────

_SEED_USERS: dict[str, User] = {
    "u1": User(id="u1", name="Alice"),
    "u2": User(id="u2", name="Bob"),
}

_SEED_PRODUCTS: dict[str, Product] = {
    "p1": Product(id="p1", name="Widget",  price_paise=1000, stock=100),
    "p2": Product(id="p2", name="Gadget",  price_paise=2500, stock=50),
    "p3": Product(id="p3", name="Doohickey", price_paise=500, stock=200),
}

# ── Live state ──────────────────────────────────────────────────────────────

users: dict[str, User] = {}
products: dict[str, Product] = {}
orders: dict[str, Order] = {}
_order_counter: int = 0


def reset() -> None:
    """Restore the store to a clean seed state. Call before every test."""
    global _order_counter
    users.clear()
    products.clear()
    orders.clear()
    users.update(copy.deepcopy(_SEED_USERS))
    products.update(copy.deepcopy(_SEED_PRODUCTS))
    _order_counter = 0


def next_order_id() -> str:
    global _order_counter
    _order_counter += 1
    return f"o{_order_counter}"


def get_user(user_id: str) -> Optional[User]:
    return users.get(user_id)


def get_product(product_id: str) -> Optional[Product]:
    return products.get(product_id)


def get_order(order_id: str) -> Optional[Order]:
    return orders.get(order_id)


# Initialise on import so the store is ready even without calling reset().
reset()
