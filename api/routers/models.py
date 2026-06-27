"""Model Registry & Versioning API (issue #237, #257).

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

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from api.database import get_sync_db
from api.models.orm import ModelRegistry
from api.schemas.model_registry import (
    ModelComparisonIn,
    ModelComparisonOut,
    ModelListResponse,
    ModelRegistryIn,
    ModelRegistryOut,
    ModelRegistryUpdateIn,
    ModelSearchIn,
    ModelTagsUpdateIn,
    ModelVersionTransitionIn,
)
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

    if name:
        query = query.where(ModelRegistry.name == name)
    if status:
        query = query.where(ModelRegistry.status == status)
    if owner:
        query = query.where(ModelRegistry.owner == owner)
    if tags:
        for tag in tags:
            query = query.where(ModelRegistry.tags.contains([tag]))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

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

    return ModelListResponse(
        data=rows,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=ModelRegistryOut, status_code=status.HTTP_201_CREATED)
def create_model(body: ModelRegistryIn, db: Session = Depends(get_sync_db)):
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
        version=body.version,
        path=stored_path,
        owner=body.owner,
        tags=body.tags,
        mlflow_run_id=body.mlflow_run_id,
        metrics=body.metrics,
        status="inactive",
        parent_id=body.parent_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/{model_id}", response_model=ModelRegistryOut)
def get_model(model_id: int, db: Session = Depends(get_sync_db)):
    """Get a specific model by ID."""
    entry = db.scalar(select(ModelRegistry).where(ModelRegistry.id == model_id))
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    return entry


@router.put("/{model_id}", response_model=ModelRegistryOut)
def update_model(
    model_id: int, body: ModelRegistryUpdateIn, db: Session = Depends(get_sync_db)
):
    """Update a model."""
    entry = db.scalar(select(ModelRegistry).where(ModelRegistry.id == model_id))
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)

    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(model_id: int, db: Session = Depends(get_sync_db)):
    """Delete a model."""
    entry = db.scalar(select(ModelRegistry).where(ModelRegistry.id == model_id))
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    db.delete(entry)
    db.commit()


# Version endpoints
@router.post("/{model_id}/versions", response_model=ModelRegistryOut, status_code=status.HTTP_201_CREATED)
def create_model_version(
    model_id: int, body: ModelRegistryIn, db: Session = Depends(get_sync_db)
):
    """Create a new version for an existing model (uses the same name as the model)."""
    parent_model = db.scalar(select(ModelRegistry).where(ModelRegistry.id == model_id))
    if parent_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    # Use parent model's name if not provided
    model_name = body.name or parent_model.name

    return create_model(
        ModelRegistryIn(
            name=model_name,
            version=body.version,
            path=body.path,
            owner=body.owner,
            tags=body.tags,
            mlflow_run_id=body.mlflow_run_id,
            metrics=body.metrics,
            status=body.status,
        ),
        db,
    )


@router.get("/{model_id}/versions", response_model=list[ModelRegistryOut])
def list_model_versions(model_id: int, db: Session = Depends(get_sync_db)):
    """List all versions of a model (by model name, using the given model_id to find the name)."""
    parent_model = db.scalar(select(ModelRegistry).where(ModelRegistry.id == model_id))
    if parent_model is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")

    versions = db.scalars(
        select(ModelRegistry)
        .where(ModelRegistry.name == parent_model.name)
        .order_by(ModelRegistry.created_at.desc())
    ).all()
    return versions


@router.post("/{model_id}/versions/{version_id}/transition", response_model=ModelRegistryOut)
def transition_version_status(
    model_id: int,
    version_id: int,
    body: ModelVersionTransitionIn,
    db: Session = Depends(get_sync_db),
):
    """Transition a model version to a new status."""
    entry = db.scalar(select(ModelRegistry).where(ModelRegistry.id == version_id))
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found")

    # If transitioning to active, deactivate other versions of the same model
    if body.target_status == "active":
        db.execute(
            update(ModelRegistry)
            .where(ModelRegistry.name == entry.name, ModelRegistry.id != version_id)
            .values(status="inactive")
        )

    entry.status = body.target_status
    db.commit()
    db.refresh(entry)

    if body.target_status == "active":
        invalidate_scorer_cache()

    return entry


@router.get("/{model_id}/versions/{version_id}", response_model=ModelRegistryOut)
def get_version_details(
    model_id: int,
    version_id: int,
    db: Session = Depends(get_sync_db),
):
    """Get details of a specific model version."""
    entry = db.scalar(select(ModelRegistry).where(ModelRegistry.id == version_id))
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found")
    return entry


# Comparison endpoint
@router.post("/compare", response_model=ModelComparisonOut)
def compare_models(body: ModelComparisonIn, db: Session = Depends(get_sync_db)):
    """Compare multiple models by their IDs."""
    models = db.scalars(
        select(ModelRegistry).where(ModelRegistry.id.in_(body.model_ids))
    ).all()

    if len(models) != len(body.model_ids):
        found_ids = {m.id for m in models}
        missing_ids = [mid for mid in body.model_ids if mid not in found_ids]
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Models with IDs {missing_ids} not found",
        )

    # Calculate comparison metrics
    comparison = {
        "count": len(models),
        "metrics": {},
    }

    # Collect all metric keys across all models
    all_metric_keys = set()
    for model in models:
        if model.metrics:
            all_metric_keys.update(model.metrics.keys())

    # For each metric, show values for all models
    for key in all_metric_keys:
        comparison["metrics"][key] = {}
        for model in models:
            comparison["metrics"][key][f"model_{model.id}"] = (
                model.metrics.get(key) if model.metrics else None
            )

    return ModelComparisonOut(
        models=models,
        comparison=comparison,
    )


@router.post("/{model_id}/activate", response_model=ModelRegistryOut)
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
