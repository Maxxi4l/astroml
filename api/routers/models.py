"""Model Registry & Versioning API (issue #237).

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
from sqlalchemy.orm import Session

from api.database import get_sync_db
from api.models.orm import ModelRegistry
from api.services.scorer import invalidate_scorer_cache

router = APIRouter(prefix="/api/v1/models", tags=["models"])

MODEL_STORE_PATH = Path(os.environ.get("MODEL_STORE_PATH", "model_store"))


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
    version: Optional[str] = None
    path: str
    metrics: Optional[dict[str, Any]] = None


@router.get("", response_model=list[ModelOut])
def list_models(db: Session = Depends(get_sync_db)):
    """List all registered model versions."""
    rows = db.scalars(
        select(ModelRegistry).order_by(ModelRegistry.created_at.desc())
    ).all()
    return rows


@router.post("", response_model=ModelOut, status_code=status.HTTP_201_CREATED)
def register_model(body: RegisterModelIn, db: Session = Depends(get_sync_db)):
    """Register a new model version."""
    version = body.version or f"{body.name}_v{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    dest_dir = MODEL_STORE_PATH / body.name / version
    dest_dir.mkdir(parents=True, exist_ok=True)

    src = Path(body.path)
    if src.exists():
        dest = dest_dir / src.name
        shutil.copy2(src, dest)
        stored_path = str(dest)
    else:
        stored_path = body.path

    entry = ModelRegistry(
        name=body.name,
        version=version,
        path=stored_path,
        metrics=body.metrics,
        status="inactive",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/{model_id}/activate", response_model=ModelOut)
def activate_model(model_id: int, db: Session = Depends(get_sync_db)):
    """Activate a model version and switch serving to its checkpoint."""
    entry = db.scalar(select(ModelRegistry).where(ModelRegistry.id == model_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Model not found")

    db.execute(
        update(ModelRegistry)
        .where(ModelRegistry.name == entry.name, ModelRegistry.id != model_id)
        .values(status="inactive")
    )
    entry.status = "active"
    db.commit()
    db.refresh(entry)
    invalidate_scorer_cache()
    return entry


@router.get("/{model_id}/metrics")
def model_metrics(model_id: int, db: Session = Depends(get_sync_db)):
    """Return stored metrics for a specific model version."""
    entry = db.scalar(select(ModelRegistry).where(ModelRegistry.id == model_id))
    if entry is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return {
        "id": entry.id,
        "name": entry.name,
        "version": entry.version,
        "metrics": entry.metrics or {},
    }
