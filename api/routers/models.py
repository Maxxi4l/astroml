"""Model Registry & Versioning API (issue #237).

Endpoints
---------
GET  /api/v1/models              — List registered models
POST /api/v1/models              — Register a new model version
POST /api/v1/models/{id}/activate — Activate a specific version
GET  /api/v1/models/{id}/metrics  — Metrics history for a model version
POST /api/v1/models/compare      — Compare multiple model versions
GET  /api/v1/models/{id}/lineage  — Get lineage for a model version
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, List, Dict

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
    parent_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class RegisterModelIn(BaseModel):
    name: str
    version: Optional[str] = None
    path: str
    metrics: Optional[dict[str, Any]] = None
    parent_id: Optional[int] = None


class CompareVersionsIn(BaseModel):
    version_ids: List[int]


class MetricDelta(BaseModel):
    metric: str
    values: Dict[int, Optional[float]]
    delta: Optional[float]  # delta from first version
    best: Optional[int]  # version id with best value (higher is better)
    worst: Optional[int]  # version id with worst value


class CompareVersionsOut(BaseModel):
    versions: List[ModelOut]
    metric_deltas: List[MetricDelta]


class LineageNode(BaseModel):
    id: int
    name: str
    version: str
    metrics: Optional[dict[str, Any]]
    created_at: datetime


class LineageOut(BaseModel):
    chain: List[LineageNode]


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
    # Validate parent_id if provided
    if body.parent_id is not None:
        parent = db.scalar(select(ModelRegistry).where(ModelRegistry.id == body.parent_id))
        if parent is None:
            raise HTTPException(status_code=404, detail="Parent model not found")
    
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
        parent_id=body.parent_id,
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


@router.post("/compare", response_model=CompareVersionsOut)
def compare_versions(body: CompareVersionsIn, db: Session = Depends(get_sync_db)):
    """Compare multiple model versions and generate a report with metrics deltas."""
    if len(body.version_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 version IDs are required")
        
    # Fetch all versions
    versions = db.scalars(
        select(ModelRegistry).where(ModelRegistry.id.in_(body.version_ids))
    ).all()
    
    # Validate all versions exist
    found_ids = {v.id for v in versions}
    missing_ids = [vid for vid in body.version_ids if vid not in found_ids]
    if missing_ids:
        raise HTTPException(status_code=404, detail=f"Model versions not found: {missing_ids}")
    
    # Keep versions in the order requested
    ordered_versions = []
    for vid in body.version_ids:
        ordered_versions.append(next(v for v in versions if v.id == vid))
    
    # Collect all unique metrics
    all_metrics = set()
    for v in ordered_versions:
        if v.metrics:
            all_metrics.update(v.metrics.keys())
    
    metric_deltas: List[MetricDelta] = []
    first_version = ordered_versions[0]
    
    for metric in sorted(all_metrics):
        values: Dict[int, Optional[float]] = {}
        numeric_values: List[tuple[int, float]] = []
        
        for v in ordered_versions:
            val = v.metrics.get(metric) if v.metrics else None
            values[v.id] = val
            if isinstance(val, (int, float)):
                numeric_values.append((v.id, val))
        
        # Calculate delta from first version
        delta = None
        if numeric_values and first_version.id in values and isinstance(values[first_version.id], (int, float)):
            first_val = values[first_version.id]
            # Find last numeric value to calculate delta? Or use latest?
            # Let's use the last value in the ordered list
            last_numeric = next((val for (vid, val) in reversed(numeric_values)), None)
            if last_numeric is not None:
                delta = last_numeric - first_val
        
        # Find best and worst (higher is better assumption)
        best = None
        worst = None
        if numeric_values:
            numeric_values.sort(key=lambda x: x[1], reverse=True)
            best = numeric_values[0][0]
            worst = numeric_values[-1][0]
        
        metric_deltas.append(MetricDelta(
            metric=metric,
            values=values,
            delta=delta,
            best=best,
            worst=worst,
        ))
    
    return CompareVersionsOut(
        versions=ordered_versions,
        metric_deltas=metric_deltas,
    )


@router.get("/{model_id}/lineage", response_model=LineageOut)
def get_lineage(model_id: int, db: Session = Depends(get_sync_db)):
    """Get the parent chain (lineage) for a model version."""
    chain: List[LineageNode] = []
    current_id: Optional[int] = model_id
    
    while current_id is not None:
        entry = db.scalar(select(ModelRegistry).where(ModelRegistry.id == current_id))
        if entry is None:
            if not chain:  # if first entry is not found
                raise HTTPException(status_code=404, detail="Model not found")
            break
        
        chain.append(LineageNode(
            id=entry.id,
            name=entry.name,
            version=entry.version,
            metrics=entry.metrics,
            created_at=entry.created_at,
        ))
        
        current_id = entry.parent_id
    
    return LineageOut(chain=chain)
