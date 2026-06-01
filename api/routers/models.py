"""Model Registry & Versioning API (issue #257).

Endpoints
---------
GET  /api/v1/models              — List registered models
POST /api/v1/models              — Register a new model version
POST /api/v1/models/{id}/activate — Activate a specific version
GET  /api/v1/models/{id}/metrics  — Metrics history for a model version
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models.orm import ModelRegistry

router = APIRouter(prefix="/api/v1/models", tags=["models"])

MODEL_STORE_PATH = Path(os.environ.get("MODEL_STORE_PATH", "model_store"))


# ─── Schemas ─────────────────────────────────────────────────────────────────

class ModelOut(BaseModel):
    id: int
    name: str
    version: str
    path: str
    metrics: Optional[dict[str, Any]]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RegisterModelIn(BaseModel):
    name: str
    version: Optional[str] = None   # auto-generated if omitted
    path: str                        # source path of the .pth file
    metrics: Optional[dict[str, Any]] = None


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.get("", response_model=list[ModelOut])
async def list_models(db: AsyncSession = Depends(get_db)):
    """List all registered model versions."""
    result = await db.execute(select(ModelRegistry).order_by(ModelRegistry.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=ModelOut, status_code=status.HTTP_201_CREATED)
async def register_model(body: RegisterModelIn, db: AsyncSession = Depends(get_db)):
    """Register a new model version.

    Copies the model file into the configured MODEL_STORE_PATH and records
    the entry in the database.  Version defaults to a UTC timestamp string.
    """
    version = body.version or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest_dir = MODEL_STORE_PATH / body.name / version
    dest_dir.mkdir(parents=True, exist_ok=True)

    src = Path(body.path)
    if src.exists():
        dest = dest_dir / src.name
        shutil.copy2(src, dest)
        stored_path = str(dest)
    else:
        # Path may be a remote URI or pre-stored reference — store as-is.
        stored_path = body.path

    entry = ModelRegistry(
        name=body.name,
        version=version,
        path=stored_path,
        metrics=body.metrics,
        status="inactive",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.post("/{model_id}/activate", response_model=ModelOut)
async def activate_model(model_id: int, db: AsyncSession = Depends(get_db)):
    """Activate a model version.

    Deactivates all other versions of the same model name, then marks this
    version as ``active``.
    """
    result = await db.execute(
        select(ModelRegistry).where(ModelRegistry.id == model_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Model not found")

    # Deactivate siblings
    await db.execute(
        update(ModelRegistry)
        .where(ModelRegistry.name == entry.name, ModelRegistry.id != model_id)
        .values(status="inactive")
    )
    entry.status = "active"
    await db.commit()
    await db.refresh(entry)
    return entry


@router.get("/{model_id}/metrics")
async def model_metrics(model_id: int, db: AsyncSession = Depends(get_db)):
    """Return stored metrics for a specific model version."""
    result = await db.execute(
        select(ModelRegistry).where(ModelRegistry.id == model_id)
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"id": entry.id, "name": entry.name, "version": entry.version,
            "metrics": entry.metrics or {}}
