"""Model registry for managing ML models and their versions."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from astroml.db.schema import Model, ModelVersion
from astroml.db.session import get_session

logger = logging.getLogger(__name__)


status: Mapped[
    Literal["training", "trained", "deployed", "archived", "failed"]
] = mapped_column()

# ---------------------------------------------------------------------------
# ModelVersion State Machine
# ---------------------------------------------------------------------------

VALID_STATUS_TRANSITIONS = {
    "training": ["trained", "failed"],
    "trained": ["deployed", "archived"],
    "deployed": ["archived"],
    "archived": [],  # Terminal state
    "failed": ["training"],  # Can retry training
}

VALID_STATUSES = set(VALID_STATUS_TRANSITIONS.keys())


class InvalidStatusTransitionError(ValueError):
    """Raised when an invalid status transition is attempted."""
    pass

class ModelRegistry:
    """Core class for managing ML models and their versions in the database.

    Provides CRUD operations for Model and ModelVersion entities,
    with helper methods for common registry operations.
    """

    def __init__(self, session: Optional[Session] = None):
        """Initialize the registry.

        Args:
            session: Optional SQLAlchemy session. If not provided, creates a new session.
        """
        self._session = session
        self._owns_session = session is None

    @property
    def session(self) -> Session:
        """Get the SQLAlchemy session, creating one if needed."""
        if self._session is None:
            self._session = get_session()
        return self._session

    def close(self) -> None:
        """Close the session if we own it."""
        if self._owns_session and self._session is not None:
            self._session.close()
            self._session = None

    def __enter__(self) -> "ModelRegistry":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Model CRUD operations
    # ------------------------------------------------------------------

    def create_model(
        self,
        name: str,
        framework: str,
        task_type: str,
        description: Optional[str] = None,
        is_active: bool = True,
    ) -> Model:
        """Create a new model.

        Args:
            name: Unique model name
            framework: ML framework (pytorch, tensorflow, sklearn, etc.)
            task_type: Task type (classification, regression, etc.)
            description: Optional model description
            is_active: Whether the model is active

        Returns:
            Created Model instance

        Raises:
            ValueError: If a model with the same name already exists
        """
        existing = self.get_model_by_name(name)
        if existing:
            raise ValueError(f"Model with name '{name}' already exists")

        model = Model(
            name=name,
            description=description,
            framework=framework,
            task_type=task_type,
            is_active=is_active,
        )
        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)
        logger.info("Created model: %s (id=%d)", name, model.id)
        return model

    def get_model(self, model_id: int) -> Optional[Model]:
        """Get a model by ID.

        Args:
            model_id: Model ID

        Returns:
            Model instance or None if not found
        """
        return self.session.get(Model, model_id)

    def get_model_by_name(self, name: str) -> Optional[Model]:
        """Get a model by name.

        Args:
            name: Model name

        Returns:
            Model instance or None if not found
        """
        stmt = select(Model).where(Model.name == name)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_models(
        self,
        framework: Optional[str] = None,
        task_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[Model]:
        """List models with optional filters.

        Args:
            framework: Filter by framework
            task_type: Filter by task type
            is_active: Filter by active status

        Returns:
            List of Model instances
        """
        stmt = select(Model)
        if framework:
            stmt = stmt.where(Model.framework == framework)
        if task_type:
            stmt = stmt.where(Model.task_type == task_type)
        if is_active is not None:
            stmt = stmt.where(Model.is_active == is_active)
        stmt = stmt.order_by(Model.created_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    def update_model(
        self,
        model_id: int,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Model]:
        """Update a model.

        Args:
            model_id: Model ID
            description: New description
            is_active: New active status

        Returns:
            Updated Model instance or None if not found
        """
        model = self.get_model(model_id)
        if not model:
            return None

        if description is not None:
            model.description = description
        if is_active is not None:
            model.is_active = is_active

        self.session.commit()
        self.session.refresh(model)
        logger.info("Updated model: %s (id=%d)", model.name, model.id)
        return model

    def delete_model(self, model_id: int) -> bool:
        """Delete a model and all its versions.

        Args:
            model_id: Model ID

        Returns:
            True if deleted, False if not found
        """
        model = self.get_model(model_id)
        if not model:
            return False

        self.session.delete(model)
        self.session.commit()
        logger.info("Deleted model: %s (id=%d)", model.name, model_id)
        return True

    # ------------------------------------------------------------------
    # ModelVersion CRUD operations
    # ------------------------------------------------------------------

    def create_model_version(
        self,
        model_id: int,
        version: str,
        artifact_path: str,
        hyperparameters: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        status: str = "training",
    ) -> ModelVersion:
        """Create a new model version.

        Args:
            model_id: Parent model ID
            version: Version string (e.g., "1.0.0")
            artifact_path: Path to model artifacts
            hyperparameters: Optional hyperparameters dict
            metrics: Optional metrics dict
            status: Version status (training, trained, deployed, etc.)

        Returns:
            Created ModelVersion instance

        Raises:
            ValueError: If model not found or version already exists for this model
        """
        model = self.get_model(model_id)
        if not model:
            raise ValueError(f"Model with id {model_id} not found")

        existing = self.get_model_version(model_id, version)
        if existing:
            raise ValueError(f"Version '{version}' already exists for model {model_id}")

        model_version = ModelVersion(
            model_id=model_id,
            version=version,
            artifact_path=artifact_path,
            hyperparameters=hyperparameters,
            metrics=metrics,
            status=status,
        )
        self.session.add(model_version)
        self.session.commit()
        self.session.refresh(model_version)
        logger.info(
            "Created model version: %s (id=%d, model_id=%d)",
            version,
            model_version.id,
            model_id,
        )
        return model_version

    def get_model_version(self, model_id: int, version: str) -> Optional[ModelVersion]:
        """Get a specific model version.

        Args:
            model_id: Model ID
            version: Version string

        Returns:
            ModelVersion instance or None if not found
        """
        stmt = select(ModelVersion).where(
            ModelVersion.model_id == model_id, ModelVersion.version == version
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_model_version_by_id(self, version_id: int) -> Optional[ModelVersion]:
        """Get a model version by ID.

        Args:
            version_id: ModelVersion ID

        Returns:
            ModelVersion instance or None if not found
        """
        return self.session.get(ModelVersion, version_id)

    def list_model_versions(
        self,
        model_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[ModelVersion]:
        """List model versions with optional filters.

        Args:
            model_id: Filter by model ID
            status: Filter by status

        Returns:
            List of ModelVersion instances
        """
        stmt = select(ModelVersion)
        if model_id:
            stmt = stmt.where(ModelVersion.model_id == model_id)
        if status:
            stmt = stmt.where(ModelVersion.status == status)
        stmt = stmt.order_by(ModelVersion.created_at.desc())
        return list(self.session.execute(stmt).scalars().all())

    def update_model_version(
        self,
        version_id: int,
        status: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
        deployed_at: Optional[datetime] = None,
def update_status(
    new_status: str,
    validate_transition: bool = True,
) -> None:
    ...

    ) -> Optional[ModelVersion]:
        """Update a model version.

        Args:
            version_id: ModelVersion ID
            status: New status
            metrics: New or updated metrics
            deployed_at: Deployment timestamp
        Args:
            new_status: The new status to set
            validate_transition: Whether to validate status transitions (default: True)

        Returns:
            Updated ModelVersion instance or None if not found

        Raises:
            InvalidStatusTransitionError: If status transition is invalid

        """
        version = self.get_model_version_by_id(version_id)
        if not version:
            return None

        if status is not None:
if validate_transition:
    self._validate_status_transition(version.status, status)

            version.status = status
        if metrics is not None:
            version.metrics = metrics
        if deployed_at is not None:
            version.deployed_at = deployed_at

        self.session.commit()
        self.session.refresh(version)
        logger.info("Updated model version: %s (id=%d)", version.version, version_id)
        return version

    def delete_model_version(self, version_id: int) -> bool:
        """Delete a model version.

        Args:
            version_id: ModelVersion ID

        Returns:
            True if deleted, False if not found
        """
        version = self.get_model_version_by_id(version_id)
        if not version:
            return False

        self.session.delete(version)
        self.session.commit()
        logger.info("Deleted model version: %s (id=%d)", version.version, version_id)
        return True

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def get_latest_version(self, model_id: int) -> Optional[ModelVersion]:
        """Get the latest version of a model by creation time.

        Args:
            model_id: Model ID

        Returns:
            Latest ModelVersion or None if no versions exist
        """
        stmt = (
            select(ModelVersion)
            .where(ModelVersion.model_id == model_id)
            .order_by(ModelVersion.created_at.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_deployed_version(self, model_id: int) -> Optional[ModelVersion]:
        """Get the deployed version of a model.

        Args:
            model_id: Model ID

        Returns:
            Deployed ModelVersion or None if no deployed version exists
        """
        stmt = (
            select(ModelVersion)
            .where(ModelVersion.model_id == model_id, ModelVersion.status == "deployed")
            .order_by(ModelVersion.deployed_at.desc())
            .limit(1)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def mark_deployed(self, version_id: int) -> Optional[ModelVersion]:
        """Mark a model version as deployed.

        Args:
            version_id: ModelVersion ID

        Returns:
            Updated ModelVersion or None if not found
def mark_deployed(self, version_id: int) -> Optional[ModelVersion]:
    """Mark a model version as deployed.

    Args:
        version_id: ModelVersion ID

    Returns:
        Updated ModelVersion instance or None if not found

    Raises:
        InvalidStatusTransitionError: If version cannot be deployed
    """
    return self.update_model_version(
        version_id,
        status="deployed",
        deployed_at=datetime.now(datetime.UTC),
    )

# ------------------------------------------------------------------
# State machine methods
# ------------------------------------------------------------------

@staticmethod
def _validate_status_transition(from_status: str, to_status: str) -> None:
    """Validate that a status transition is allowed.

    Args:
        from_status: Current status
        to_status: Target status

    Raises:
        InvalidStatusTransitionError: If transition is not allowed
    """
    if to_status not in VALID_STATUSES:
        raise InvalidStatusTransitionError(f"Invalid target status: '{to_status}'")

    if from_status == to_status:
        return  # No-op transition is allowed

    allowed_transitions = VALID_STATUS_TRANSITIONS.get(from_status, [])
    if to_status not in allowed_transitions:
        raise InvalidStatusTransitionError(
            f"Cannot transition from '{from_status}' to '{to_status}'. "
            f"Allowed transitions from '{from_status}': {allowed_transitions}"
        )
