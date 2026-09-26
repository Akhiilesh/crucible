# PR-1 — Add Refund Endpoint

**Type:** Feature  
**Branch:** pr-1-refunds  
**Refs:** R15, R16, R17, R18, R19, R20

## Summary

Implement `POST /orders/{id}/refund` so customers can claim refunds on delivered orders within
the allowed window.

## Acceptance criteria

- AC1: Returns 400 if the order is not in "delivered" status (R15).
- AC2: Returns 400 if more than 14 days have passed since delivered_at (R16, R17).
- AC3: Returns 400 if the refund amount is ≤ 0 or > order total (R18).
- AC4: Returns 400 if the order has already been refunded (R19).
- AC5: On success, sets order status to "refunded" and returns 200 (R20).
