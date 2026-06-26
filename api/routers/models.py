"""Model Registry & Versioning API (issue #237, #257).

Endpoints
---------
GET     /api/v1/models              — List registered models
POST    /api/v1/models              — Register a new model version
GET     /api/v1/models/{model_id}   — Get a specific model
PUT     /api/v1/models/{model_id}   — Update a model
DELETE  /api/v1/models/{model_id}   — Delete a model
POST    /api/v1/models/{model_id}/versions — Create a new version for a model
GET     /api/v1/models/{model_id}/versions — List all versions of a model
POST    /api/v1/models/{model_id}/versions/{version_id}/transition — Transition version status
GET     /api/v1/models/{model_id}/versions/{version_id} — Get version details
POST    /api/v1/models/compare     — Compare multiple models
POST    /api/v1/models/{id}/activate — Activate a specific version
GET     /api/v1/models/{id}/metrics  — Metrics history for a model version
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

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


@router.get("", response_model=ModelListResponse)
def list_models(
    db: Session = Depends(get_sync_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    name: Optional[str] = None,
    status: Optional[str] = None,
    owner: Optional[str] = None,
    tags: Optional[list[str]] = Query(None),
):
    """List all registered model versions with pagination and filtering."""
    query = select(ModelRegistry)

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

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.order_by(ModelRegistry.created_at.desc()).offset(offset).limit(page_size)
    rows = db.scalars(query).all()

    return ModelListResponse(
        data=rows,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("", response_model=ModelRegistryOut, status_code=status.HTTP_201_CREATED)
def create_model(body: ModelRegistryIn, db: Session = Depends(get_sync_db)):
    """Register a new model version."""
    # Check if name+version already exists
    existing = db.scalar(
        select(ModelRegistry).where(
            ModelRegistry.name == body.name, ModelRegistry.version == body.version
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model with name '{body.name}' and version '{body.version}' already exists",
        )

    dest_dir = MODEL_STORE_PATH / body.name / body.version
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
        status=body.status or "inactive",
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


@router.post("/search", response_model=ModelListResponse)
def search_models(body: ModelSearchIn, db: Session = Depends(get_sync_db)):
    """Full-text search across models (name, version, owner, tags)."""
    search_query = body.query.lower()
    query = select(ModelRegistry)

    # Search across relevant fields
    conditions = []
    conditions.append(func.lower(ModelRegistry.name).contains(search_query))
    conditions.append(func.lower(ModelRegistry.version).contains(search_query))
    if ModelRegistry.owner is not None:
        conditions.append(func.lower(ModelRegistry.owner).contains(search_query))
    
    # Combine conditions with OR
    from sqlalchemy import or_
    query = query.where(or_(*conditions))
    
    # Also search in tags if tags exist
    # Note: JSON tag search is database-specific, but we'll implement a basic version
    # For PostgreSQL, we could use jsonb functions, but let's keep it generic for now

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    # Get paginated results
    offset = (body.page - 1) * body.page_size
    query = query.order_by(ModelRegistry.created_at.desc()).offset(offset).limit(body.page_size)
    rows = db.scalars(query).all()

    return ModelListResponse(
        data=rows,
        page=body.page,
        page_size=body.page_size,
        total=total,
    )


@router.post("/{model_id}/tags", response_model=ModelRegistryOut)
def update_model_tags(
    model_id: int, body: ModelTagsUpdateIn, db: Session = Depends(get_sync_db)
):
    """Add or remove tags from a model."""
    entry = db.scalar(select(ModelRegistry).where(ModelRegistry.id == model_id))
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model not found")
    
    current_tags = entry.tags or []
    current_tags_set = set(current_tags)
    
    # Add tags
    if body.add_tags:
        for tag in body.add_tags:
            current_tags_set.add(tag)
    
    # Remove tags
    if body.remove_tags:
        for tag in body.remove_tags:
            if tag in current_tags_set:
                current_tags_set.remove(tag)
    
    # Update entry
    entry.tags = list(current_tags_set)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/by-tag/{tag}", response_model=ModelListResponse)
def get_models_by_tag(
    tag: str,
    db: Session = Depends(get_sync_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Get all models that have a specific tag."""
    query = select(ModelRegistry).where(ModelRegistry.tags.contains([tag]))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    # Get paginated results
    offset = (page - 1) * page_size
    query = query.order_by(ModelRegistry.created_at.desc()).offset(offset).limit(page_size)
    rows = db.scalars(query).all()

    return ModelListResponse(
        data=rows,
        page=page,
        page_size=page_size,
        total=total,
    )
