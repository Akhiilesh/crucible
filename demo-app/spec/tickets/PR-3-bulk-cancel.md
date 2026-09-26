# PR-3 — Add Bulk Cancel Endpoint

**Type:** Feature  
**Branch:** pr-3-bulk-cancel  
**Refs:** R25, R26, R27, R28

## Summary

Implement `POST /orders/bulk-cancel` so admins or users can cancel multiple placed orders in one
request.

## Acceptance criteria

- AC1: Returns 400 if the order ID list is empty (R26).
- AC2: Stock is restored only for orders that transition from "placed" to "cancelled" (R27).
- AC3: Orders not in "placed" status are skipped silently — no error (R28).
- AC4: Returns a summary of how many orders were cancelled.
