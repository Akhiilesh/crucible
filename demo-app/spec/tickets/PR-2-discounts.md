# PR-2 — Add Discount Code Endpoint

**Type:** Feature  
**Branch:** pr-2-discounts  
**Refs:** R21, R22, R23, R24

## Summary

Implement `POST /orders/{id}/discount` so owners can apply a percentage discount to a placed order.

## Acceptance criteria

- AC1: Returns 403 if the caller is not the order owner (R22).
- AC2: Returns 400 if the discount percentage is < 1 or > 50 (R21, R24).
- AC3: The new total must never go below 0 (R23).
- AC4: On success, updates total_paise and returns 200.
