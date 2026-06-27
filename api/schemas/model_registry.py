"""Pydantic schemas for model registry."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Model registry schemas
class ModelRegistryIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    version: str = Field(..., min_length=1, max_length=64)
    path: str = Field(..., min_length=1)
    owner: Optional[str] = Field(None, max_length=128)
    tags: Optional[List[str]] = None
    mlflow_run_id: Optional[str] = Field(None, max_length=128)
    metrics: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(default="inactive", pattern="^(inactive|active|deprecated)$")


class ModelRegistryUpdateIn(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    version: Optional[str] = Field(None, min_length=1, max_length=64)
    path: Optional[str] = Field(None, min_length=1)
    owner: Optional[str] = Field(None, max_length=128)
    tags: Optional[List[str]] = None
    mlflow_run_id: Optional[str] = Field(None, max_length=128)
    metrics: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, pattern="^(inactive|active|deprecated)$")


class ModelRegistryOut(BaseModel):
    id: int
    name: str
    version: str
    path: str
    owner: Optional[str]
    tags: Optional[List[str]]
    mlflow_run_id: Optional[str]
    metrics: Optional[Dict[str, Any]]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ModelListResponse(BaseModel):
    data: List[ModelRegistryOut]
    page: int
    page_size: int
    total: int


class ModelVersionTransitionIn(BaseModel):
    target_status: str = Field(..., pattern="^(inactive|active|deprecated)$")


class ModelComparisonIn(BaseModel):
    model_ids: List[int] = Field(..., min_length=2)


class ModelComparisonOut(BaseModel):
    models: List[ModelRegistryOut]
    comparison: Dict[str, Any]


class ModelSearchIn(BaseModel):
    query: str
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class ModelTagsUpdateIn(BaseModel):
    add_tags: Optional[List[str]] = None
    remove_tags: Optional[List[str]] = None

