## Summary

This PR implements four production features for the AstroML API: model registry with version rollback, batch fraud scoring scheduler, real-time WebSocket streaming, and JWT/API-key authentication with rate limiting.

## Purpose / Motivation

These features are required for production deployment — managing model checkpoints safely, keeping fraud alerts up-to-date without manual scoring, powering the live dashboard, and securing all API endpoints.

## Changes Made

- **#237 Model Registry & Versioning** — Mounted `/api/v1/models` routes; models register with `{name}_v{timestamp}` versioning, store checkpoints locally, and activation invalidates the scorer cache for rollback.
- **#238 Batch Scoring Scheduler** — Fixed lifespan wiring to use the async session factory; scheduler scores active accounts every 5 minutes, writes to `api_fraud_alerts`, purges alerts older than 90 days, and broadcasts new alerts over WebSocket.
- **#239 Real-time WebSocket Endpoint** — Added `/api/v1/ws/transactions` and `/api/v1/ws/alerts` with token auth, 30s heartbeat ping/pong, per-connection rate limiting, and frontend `subscribeToIncomingTransactions` integration.
- **#240 Authentication & API Keys** — JWT login/refresh, API key generation with scoped permissions, auth middleware (401/429), and default admin seeding; auth disabled in test suite via `AUTH_ENABLED=false`.

## How to Test

1. **Auth** — `POST /api/v1/auth/login` with `{"username":"admin","password":"admin123"}` → receive JWT. Call `/api/v1/fraud/alerts` without token → 401.
2. **Model registry** — `POST /api/v1/models` with a `.pth` path → 201. `POST /api/v1/models/{id}/activate` → status `active`. `GET /api/v1/models/{id}/metrics` → stored metrics.
3. **Batch scheduler** — Start API; wait 5 min (or set `BATCH_INTERVAL_SECONDS=10`). Check logs for batch metrics and new rows in `api_fraud_alerts`.
4. **WebSocket** — Connect to `ws://localhost:8000/api/v1/ws/transactions?token=<jwt>`. Receive `{"type":"transaction","data":{...}}` messages. Send `pong` in response to `ping`.
5. **Frontend** — Open dashboard; real-time transaction chart should populate when new transactions arrive.

## Breaking Changes

- Fraud alert schema unified on `api_fraud_alerts` (`risk_score`, `detected_at` fields). Clients using the old `fraud_alerts` table fields should migrate.
- API endpoints require authentication when `AUTH_ENABLED=true` (default). Set `AUTH_ENABLED=false` for local dev without tokens.

## Related Issues

Closes Traqora/astroml#237
Closes Traqora/astroml#238
Closes Traqora/astroml#239
Closes Traqora/astroml#240

## Checklist

- [x] Code builds successfully
- [x] Tests added/updated
- [x] No console errors
- [x] Documentation updated (if needed)
