"""Real-time WebSocket endpoints (issue #239).

Endpoints
---------
ws://host/api/v1/ws/transactions?token=xxx — Stream new transactions
ws://host/api/v1/ws/alerts?token=xxx       — Stream new fraud alerts
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import authenticate_token
from api.database import _async_session_factory, _sync_session_factory
from api.websocket.manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ws", tags=["websocket"])


async def _authenticate_ws(token: str | None) -> bool:
    if not token:
        return False
    from api.database import _sync_session_factory

    session = _sync_session_factory()()
    try:
        authenticate_token(token, session)
        return True
    except Exception:  # noqa: BLE001
        return False
    finally:
        session.close()


@router.websocket("/transactions")
async def ws_transactions(
    websocket: WebSocket,
    token: str | None = Query(None),
):
    """Stream new transactions to connected dashboard clients."""
    if not await _authenticate_ws(token):
        await websocket.close(code=1008, reason="Unauthorized")
        return

    client = await ws_manager.connect(websocket, "transactions")
    heartbeat = asyncio.create_task(ws_manager.heartbeat_loop(client))
    try:
        while True:
            raw = await websocket.receive_text()
            if raw == "pong":
                ws_manager.record_pong(client)
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat.cancel()
        await ws_manager.disconnect(client)


@router.websocket("/alerts")
async def ws_alerts(
    websocket: WebSocket,
    token: str | None = Query(None),
):
    """Stream new fraud alerts to connected dashboard clients."""
    if not await _authenticate_ws(token):
        await websocket.close(code=1008, reason="Unauthorized")
        return

    client = await ws_manager.connect(websocket, "alerts")
    heartbeat = asyncio.create_task(ws_manager.heartbeat_loop(client))
    try:
        while True:
            raw = await websocket.receive_text()
            if raw == "pong":
                ws_manager.record_pong(client)
    except WebSocketDisconnect:
        pass
    finally:
        heartbeat.cancel()
        await ws_manager.disconnect(client)


async def poll_and_broadcast_transactions(interval_seconds: int = 5) -> None:
    """Background task: broadcast newly inserted transactions."""
    from api.models.orm import ApiTransaction as Transaction  # noqa: PLC0415

    last_seen: str | None = None
    factory = _async_session_factory()

    while True:
        try:
            async with factory() as db:
                q = select(Transaction).order_by(Transaction.created_at.desc()).limit(20)
                result = await db.execute(q)
                rows = list(result.scalars().all())

            for tx in reversed(rows):
                if last_seen and tx.hash <= last_seen:
                    continue
                await ws_manager.broadcast("transactions", {
                    "type": "transaction",
                    "data": {
                        "hash": tx.hash,
                        "ledgerSequence": tx.ledger_sequence,
                        "sourceAccount": tx.source_account,
                        "destinationAccount": tx.destination_account,
                        "amount": float(tx.amount) if tx.amount is not None else None,
                        "assetCode": tx.asset_code,
                        "fee": tx.fee,
                        "successful": tx.successful,
                        "createdAt": tx.created_at.isoformat(),
                    },
                })

            if rows:
                last_seen = rows[0].hash
        except Exception as exc:  # noqa: BLE001
            logger.debug("Transaction poll error: %s", exc)

        await asyncio.sleep(interval_seconds)
