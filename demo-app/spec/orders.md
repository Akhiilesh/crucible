# Orders Service — Product Specification

Each rule is identified by its ID (R1, R2, …). These IDs are the canonical `basis` values for
Crucible proof findings. Every rule is one plain English line.

---

## Orders

R1: An order must contain at least one item.
R2: Each item's quantity must be at least 1.
R3: Creating an order reduces the stock of each product by the ordered quantity.
R4: An order cannot be created if any product has insufficient stock.
R5: The order total is the sum of (product price × quantity) for all items, in paise.
R6: A newly created order has status "placed".
R7: Only the user who created an order may read, modify, or cancel it.
R8: Accessing another user's order returns 403.

## Delivery

R9: A placed order can be delivered via POST /orders/{id}/deliver.
R10: Delivering an order sets its status to "delivered" and records delivered_at.
R11: Only placed orders can be delivered; any other status returns 400.

## Cancellation

R12: A placed order can be cancelled via POST /orders/{id}/cancel.
R13: Cancelling an order restores the stock of each item to its pre-order level.
R14: Only placed orders can be cancelled; any other status returns 400.

## Refunds

R15: Refunds are only allowed for delivered orders.
R16: The refund window is 14 days counted from delivered_at, not created_at.
R17: A refund request outside the 14-day window from delivered_at must return 400.
R18: The refund amount must be greater than 0 and at most the order total.
R19: A refunded order cannot be refunded again.
R20: A successful refund sets the order status to "refunded".

## Discounts

R21: A discount code gives a percentage off the order total, between 1 and 50 inclusive.
R22: A discount can only be applied by the owner of the order.
R23: The order total after a discount can never go below 0.
R24: A discount percentage outside the range 1–50 must return 400.

## Bulk cancel

R25: POST /orders/bulk-cancel accepts a list of order IDs and cancels each eligible order.
R26: An empty list of order IDs must return 400.
R27: Stock is restored only for orders that were actually cancelled by this request.
R28: Orders that are not in "placed" status are silently skipped during bulk cancel.
