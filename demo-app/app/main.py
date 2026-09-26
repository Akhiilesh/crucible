"""FastAPI orders service — with bulk-cancel endpoint (pr-3-bulk-cancel)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException

import app.store as store
from app.models import (
    BulkCancelRequest,
    BulkCancelResponse,
    CreateOrderRequest,
    Order,
    OrderResponse,
    OrderStatus,
)

app = FastAPI(title="Orders Service")


# ── Helpers ─────────────────────────────────────────────────────────────────

def _require_user(x_user_id: str) -> str:
    """Validate that the caller is a known user. Returns the user_id."""
    if not store.get_user(x_user_id):
        raise HTTPException(status_code=401, detail="Unknown user")
    return x_user_id


def _require_own_order(order_id: str, user_id: str) -> Order:
    """Return the order if it belongs to the caller; raise 403/404 otherwise."""
    order = store.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return order


def _order_to_response(order: Order) -> OrderResponse:
    return OrderResponse(**order.model_dump())


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.post("/orders", response_model=OrderResponse, status_code=201)
def create_order(
    body: CreateOrderRequest,
    x_user_id: str = Header(...),
) -> OrderResponse:
    """Create a new order. Reduces stock for each item."""
    user_id = _require_user(x_user_id)

    if not body.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    # Validate products and stock before mutating anything
    for item in body.items:
        product = store.get_product(item.product_id)
        if product is None:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id!r} not found")
        if product.stock < item.qty:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for product {item.product_id!r}",
            )

    # Compute total and deduct stock
    total_paise = 0
    for item in body.items:
        product = store.products[item.product_id]
        total_paise += product.price_paise * item.qty
        store.products[item.product_id] = product.model_copy(
            update={"stock": product.stock - item.qty}
        )

    order = Order(
        id=store.next_order_id(),
        user_id=user_id,
        items=body.items,
        total_paise=total_paise,
        status=OrderStatus.placed,
        created_at=datetime.now(tz=timezone.utc),
    )
    store.orders[order.id] = order
    return _order_to_response(order)


@app.get("/orders/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: str,
    x_user_id: str = Header(...),
) -> OrderResponse:
    """Fetch a single order. Only the owning user may read it."""
    user_id = _require_user(x_user_id)
    order = _require_own_order(order_id, user_id)
    return _order_to_response(order)


@app.post("/orders/{order_id}/deliver", response_model=OrderResponse)
def deliver_order(
    order_id: str,
    x_user_id: str = Header(...),
) -> OrderResponse:
    """Mark an order as delivered. Only valid for placed orders."""
    user_id = _require_user(x_user_id)
    order = _require_own_order(order_id, user_id)

    if order.status != OrderStatus.placed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot deliver an order with status {order.status!r}",
        )

    updated = order.model_copy(update={
        "status": OrderStatus.delivered,
        "delivered_at": datetime.now(tz=timezone.utc),
    })
    store.orders[order_id] = updated
    return _order_to_response(updated)


@app.post("/orders/bulk-cancel", response_model=BulkCancelResponse)
def bulk_cancel_orders(
    body: BulkCancelRequest,
    x_user_id: str = Header(...),
) -> BulkCancelResponse:
    """Cancel multiple placed orders in one request. Restores stock for each."""
    _require_user(x_user_id)

    if not body.order_ids:
        raise HTTPException(status_code=400, detail="order_ids must not be empty")

    cancelled: list[str] = []
    skipped: list[str] = []

    for order_id in body.order_ids:
        order = store.get_order(order_id)
        if order is None or order.status != OrderStatus.placed:
            skipped.append(order_id)
            continue

        # Restore stock for each item in this order
        for item in order.items:
            product = store.products[item.product_id]
            store.products[item.product_id] = product.model_copy(
                update={"stock": product.stock + item.qty}
            )

        store.orders[order_id] = order.model_copy(update={"status": OrderStatus.cancelled})
        cancelled.append(order_id)

    return BulkCancelResponse(
        cancelled=cancelled,
        skipped=skipped,
        cancelled_count=len(cancelled),
    )


@app.post("/orders/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: str,
    x_user_id: str = Header(...),
) -> OrderResponse:
    """Cancel a placed order. Restores stock. Only valid for placed orders."""
    user_id = _require_user(x_user_id)
    order = _require_own_order(order_id, user_id)

    if order.status != OrderStatus.placed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel an order with status {order.status!r}",
        )

    # Restore stock for each item
    for item in order.items:
        product = store.products[item.product_id]
        store.products[item.product_id] = product.model_copy(
            update={"stock": product.stock + item.qty}
        )

    updated = order.model_copy(update={"status": OrderStatus.cancelled})
    store.orders[order_id] = updated
    return _order_to_response(updated)
