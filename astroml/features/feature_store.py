"""Feature Store implementation for AstroML.

This module provides a comprehensive feature store that centralizes feature computation,
storage, versioning, and retrieval for machine learning workflows. It integrates with
existing feature modules while adding enterprise-grade feature management capabilities.

Key Features:
- Feature definition and registration
- Computed feature storage and caching
- Feature versioning and lineage tracking
- Time-travel and point-in-time queries
- Feature metadata and documentation
- Integration with existing feature modules
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Set,
    Union,
    Callable,
    Protocol,
    runtime_checkable,
)
from enum import Enum
from pathlib import Path
import pickle
import sqlite3
from contextlib import contextmanager

import pandas as pd
import numpy as np

from astroml.features.schema_validation import (
    validate_dataframe,
    dry_run_ingestion,
    ValidationResult,
    FEATURE_VALUE_SCHEMA,
)

from ..cache import cache_feature_store


logger = logging.getLogger(__name__)


class FeatureType(Enum):
    """Supported feature data types."""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    TEXT = "text"
    VECTOR = "vector"
    TIME_SERIES = "time_series"


class FeatureStatus(Enum):
    """Feature lifecycle status."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass
class FeatureDefinition:
    """Definition of a feature in the feature store.
    
    Attributes:
        name: Unique feature name
        description: Human-readable description
        feature_type: Data type of the feature
        computation_function: Function to compute the feature
        parameters: Parameters for the computation function
        tags: List of tags for categorization
        owner: Feature owner/team
        status: Feature lifecycle status
        version: Feature version
        created_at: Creation timestamp
        updated_at: Last update timestamp
        metadata: Additional metadata
    """
    
    name: str
    description: str
    feature_type: FeatureType
    computation_function: Optional[Callable] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    owner: str = ""
    status: FeatureStatus = FeatureStatus.DEVELOPMENT
    version: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Generate feature ID and validate definition."""
        self.feature_id = f"{self.name}_v{self.version}"
        
    @property
    def feature_id(self) -> str:
        """Unique feature identifier."""
        return f"{self.name}_v{self.version}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "feature_type": self.feature_type.value,
            "parameters": self.parameters,
            "tags": self.tags,
            "owner": self.owner,
            "status": self.status.value,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FeatureDefinition:
        """Create from dictionary representation."""
        data = data.copy()
        data["feature_type"] = FeatureType(data["feature_type"])
        data["status"] = FeatureStatus(data["status"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


@dataclass
class FeatureValue:
    """Container for computed feature values with metadata.
    
    Attributes:
        feature_id: Feature identifier
        entity_id: Entity identifier (account, transaction, etc.)
        value: Feature value
        timestamp: Feature computation timestamp
        validity_period: Period during which feature is valid
        metadata: Additional metadata
    """
    
    feature_id: str
    entity_id: str
    value: Any
    timestamp: datetime
    validity_period: Optional[timedelta] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def expires_at(self) -> Optional[datetime]:
        """Expiration timestamp for the feature value."""
        if self.validity_period:
            return self.timestamp + self.validity_period
        return None
    
    def is_valid_at(self, timestamp: datetime) -> bool:
        """Check if feature value is valid at given timestamp."""
        if self.expires_at and timestamp > self.expires_at:
            return False
        return timestamp >= self.timestamp


@dataclass
class FeatureSet:
    """Collection of related features for a specific use case.
    
    Attributes:
        name: Feature set name
        description: Feature set description
        feature_ids: List of feature identifiers
        entity_type: Type of entity (account, transaction, etc.)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        metadata: Additional metadata
    """
    
    name: str
    description: str
    feature_ids: List[str]
    entity_type: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "feature_ids": self.feature_ids,
            "entity_type": self.entity_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@runtime_checkable
class FeatureComputer(Protocol):
    """Protocol for feature computation functions."""
    
    def __call__(
        self,
        data: pd.DataFrame,
        entity_col: str,
        timestamp_col: str,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Compute features from input data.
        
        Args:
            data: Input DataFrame
            entity_col: Entity identifier column
            timestamp_col: Timestamp column
            **kwargs: Additional parameters
            
        Returns:
            DataFrame with computed features indexed by entity
        """
        ...


class FeatureStorage:
    """Storage backend for feature values and metadata."""
    
    def __init__(self, storage_path: Union[str, Path]):
        """Initialize storage backend.
        
        Args:
            storage_path: Path to storage directory
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize SQLite database for metadata
        self.db_path = self.storage_path / "feature_store.db"
        self._init_database()
        
        # Directory for feature data
        self.data_path = self.storage_path / "data"
        self.data_path.mkdir(exist_ok=True)
    
    def _init_database(self) -> None:
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS feature_definitions (
                    feature_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    description TEXT,
                    feature_type TEXT NOT NULL,
                    parameters TEXT,
                    tags TEXT,
                    owner TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                );
                
                CREATE TABLE IF NOT EXISTS feature_sets (
                    name TEXT PRIMARY KEY,
                    description TEXT,
                    feature_ids TEXT,
                    entity_type TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                );
                
                CREATE TABLE IF NOT EXISTS feature_lineage (
                    feature_id TEXT,
                    parent_feature_id TEXT,
                    relationship_type TEXT,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (feature_id, parent_feature_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_feature_definitions_name 
                    ON feature_definitions(name);
                
                CREATE INDEX IF NOT EXISTS idx_feature_definitions_status 
                    ON feature_definitions(status);
            """)
    
    def store_feature_definition(self, feature_def: FeatureDefinition) -> None:
        """Store feature definition in database.
        
        Args:
            feature_def: Feature definition to store
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO feature_definitions 
                (feature_id, name, version, description, feature_type, 
                 parameters, tags, owner, status, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feature_def.feature_id,
                    feature_def.name,
                    feature_def.version,
                    feature_def.description,
                    feature_def.feature_type.value,
                    json.dumps(feature_def.parameters),
                    json.dumps(feature_def.tags),
                    feature_def.owner,
                    feature_def.status.value,
                    feature_def.created_at.isoformat(),
                    feature_def.updated_at.isoformat(),
                    json.dumps(feature_def.metadata),
                ),
            )
    
    def get_feature_definition(self, feature_id: str) -> Optional[FeatureDefinition]:
        """Retrieve feature definition by ID.
        
        Args:
            feature_id: Feature identifier
            
        Returns:
            Feature definition if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM feature_definitions WHERE feature_id = ?",
                (feature_id,),
            )
            row = cursor.fetchone()
            
            if row:
                columns = [
                    "feature_id", "name", "version", "description", "feature_type",
                    "parameters", "tags", "owner", "status", "created_at", 
                    "updated_at", "metadata"
                ]
                data = dict(zip(columns, row))
                data["parameters"] = json.loads(data["parameters"])
                data["tags"] = json.loads(data["tags"])
                data["metadata"] = json.loads(data["metadata"])
                return FeatureDefinition.from_dict(data)
            
            return None
    
    def list_feature_definitions(
        self,
        status: Optional[FeatureStatus] = None,
        tags: Optional[List[str]] = None,
        owner: Optional[str] = None,
    ) -> List[FeatureDefinition]:
        """List feature definitions with optional filtering.
        
        Args:
            status: Filter by status
            tags: Filter by tags (must contain all specified tags)
            owner: Filter by owner
            
        Returns:
            List of feature definitions
        """
        query = "SELECT * FROM feature_definitions WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        if owner:
            query += " AND owner = ?"
            params.append(owner)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            features = []
            for row in rows:
                columns = [
                    "feature_id", "name", "version", "description", "feature_type",
                    "parameters", "tags", "owner", "status", "created_at", 
                    "updated_at", "metadata"
                ]
                data = dict(zip(columns, row))
                data["parameters"] = json.loads(data["parameters"])
                data["tags"] = json.loads(data["tags"])
                data["metadata"] = json.loads(data["metadata"])
                
                # Filter by tags if specified
                if tags:
                    feature_tags = set(data["tags"])
                    if not all(tag in feature_tags for tag in tags):
                        continue
                
                features.append(FeatureDefinition.from_dict(data))
            
            return features
    
    def store_feature_values(
        self,
        feature_id: str,
        values: pd.DataFrame,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store computed feature values.
        
        Args:
            feature_id: Feature identifier
            values: DataFrame with feature values indexed by entity
            metadata: Additional metadata
        """
        # Store as parquet file for efficient storage and retrieval
        file_path = self.data_path / f"{feature_id}.parquet"
        
        # Add metadata to DataFrame
        if metadata:
            values.attrs["metadata"] = metadata
            values.attrs["feature_id"] = feature_id
            values.attrs["stored_at"] = datetime.utcnow().isoformat()
        
        values.to_parquet(file_path, index=True)
        logger.info(f"Stored {len(values)} feature values for {feature_id}")
    
    def get_feature_values(
        self,
        feature_id: str,
        entity_ids: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None,
    ) -> Optional[pd.DataFrame]:
        """Retrieve stored feature values.
        
        Args:
            feature_id: Feature identifier
            entity_ids: Optional list of entity IDs to filter
            timestamp: Optional timestamp for point-in-time queries
            
        Returns:
            DataFrame with feature values if found, None otherwise
        """
        file_path = self.data_path / f"{feature_id}.parquet"
        
        if not file_path.exists():
            return None
        
        values = pd.read_parquet(file_path)
        
        # Filter by entity IDs if specified
        if entity_ids:
            values = values[values.index.isin(entity_ids)]
        
        # TODO: Implement point-in-time filtering if timestamp is provided
        # This would require storing multiple versions of feature values
        
        return values
    
    def store_feature_set(self, feature_set: FeatureSet) -> None:
        """Store feature set definition.
        
        Args:
            feature_set: Feature set to store
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO feature_sets 
                (name, description, feature_ids, entity_type, 
                 created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    feature_set.name,
                    feature_set.description,
                    json.dumps(feature_set.feature_ids),
                    feature_set.entity_type,
                    feature_set.created_at.isoformat(),
                    feature_set.updated_at.isoformat(),
                    json.dumps(feature_set.metadata),
                ),
            )
    
    def get_feature_set(self, name: str) -> Optional[FeatureSet]:
        """Retrieve feature set by name.
        
        Args:
            name: Feature set name
            
        Returns:
            Feature set if found, None otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT * FROM feature_sets WHERE name = ?",
                (name,),
            )
            row = cursor.fetchone()
            
            if row:
                columns = [
                    "name", "description", "feature_ids", "entity_type",
                    "created_at", "updated_at", "metadata"
                ]
                data = dict(zip(columns, row))
                data["feature_ids"] = json.loads(data["feature_ids"])
                data["metadata"] = json.loads(data["metadata"])
                data["created_at"] = datetime.fromisoformat(data["created_at"])
                data["updated_at"] = datetime.fromisoformat(data["updated_at"])
                
                return FeatureSet(**data)
            
            return None


class FeatureRegistry:
    """Registry for managing feature definitions and computations."""
    
    def __init__(self, storage: FeatureStorage):
        """Initialize feature registry.
        
        Args:
            storage: Storage backend
        """
        self.storage = storage
        self._computers: Dict[str, FeatureComputer] = {}
        self._register_builtin_features()
    
    def _register_builtin_features(self) -> None:
        """Register built-in feature computers from existing modules."""
        try:
            # Import existing feature modules
            from astroml.features import (
                frequency,
                structural_importance,
                node_features,
                asset_diversity,
                imbalance,
                memo,
            )
            
            # Register frequency features
            self.register_computer(
                "daily_transaction_count",
                frequency.compute_daily_transaction_counts,
                {
                    "description": "Daily transaction count per account",
                    "feature_type": FeatureType.NUMERIC,
                    "tags": ["frequency", "activity"],
                },
            )
            
            self.register_computer(
                "transaction_burstiness",
                frequency.compute_burstiness,
                {
                    "description": "Transaction burstiness metric",
                    "feature_type": FeatureType.NUMERIC,
                    "tags": ["frequency", "behavior"],
                },
            )
            
            # Register structural importance features
            self.register_computer(
                "degree_centrality",
                structural_importance.compute_degree_centrality,
                {
                    "description": "Degree centrality in transaction graph",
                    "feature_type": FeatureType.NUMERIC,
                    "tags": ["graph", "centrality"],
                },
            )
            
            self.register_computer(
                "betweenness_centrality",
                structural_importance.compute_betweenness_centrality,
                {
                    "description": "Betweenness centrality in transaction graph",
                    "feature_type": FeatureType.NUMERIC,
                    "tags": ["graph", "centrality"],
                },
            )
            
            self.register_computer(
                "pagerank",
                structural_importance.compute_pagerank,
                {
                    "description": "PageRank score in transaction graph",
                    "feature_type": FeatureType.NUMERIC,
                    "tags": ["graph", "importance"],
                },
            )
            
            # Register node features
            self.register_computer(
                "node_features",
                node_features.compute_node_features,
                {
                    "description": "Basic node features (degree, volume, age)",
                    "feature_type": FeatureType.TIME_SERIES,
                    "tags": ["node", "basic"],
                },
            )
            
            # Register asset diversity features
            self.register_computer(
                "asset_diversity",
                asset_diversity.compute_asset_diversity,
                {
                    "description": "Asset diversity metrics",
                    "feature_type": FeatureType.NUMERIC,
                    "tags": ["asset", "diversity"],
                },
            )
            
            logger.info("Registered built-in feature computers")
            
        except ImportError as e:
            logger.warning(f"Could not import some feature modules: {e}")
    
    def register_computer(
        self,
        name: str,
        computer: FeatureComputer,
        metadata: Dict[str, Any],
    ) -> None:
        """Register a feature computer.
        
        Args:
            name: Feature name
            computer: Computation function
            metadata: Feature metadata
        """
        self._computers[name] = computer
        
        # Create feature definition
        feature_def = FeatureDefinition(
            name=name,
            description=metadata.get("description", ""),
            feature_type=metadata.get("feature_type", FeatureType.NUMERIC),
            parameters=metadata.get("parameters", {}),
            tags=metadata.get("tags", []),
            owner=metadata.get("owner", "system"),
        )
        
        self.storage.store_feature_definition(feature_def)
        logger.info(f"Registered feature computer: {name}")
    
    def get_computer(self, name: str) -> Optional[FeatureComputer]:
        """Get registered feature computer.
        
        Args:
            name: Feature name
            
        Returns:
            Feature computer if found, None otherwise
        """
        return self._computers.get(name)
    
    def list_features(self) -> List[str]:
        """List all registered feature names."""
        return list(self._computers.keys())


class FeatureStore:
    """Main feature store interface.
    
    Provides a high-level API for feature registration, computation,
    storage, and retrieval.
    """
    
    def __init__(self, storage_path: Union[str, Path] = "./feature_store"):
        """Initialize feature store.
        
        Args:
            storage_path: Path to feature store storage
        """
        self.storage = FeatureStorage(storage_path)
        self.registry = FeatureRegistry(self.storage)
        self._cache: Dict[str, pd.DataFrame] = {}
    
    def register_feature(
        self,
        name: str,
        computer: FeatureComputer,
        description: str,
        feature_type: FeatureType = FeatureType.NUMERIC,
        tags: Optional[List[str]] = None,
        owner: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> FeatureDefinition:
        """Register a new feature.
        
        Args:
            name: Feature name
            computer: Computation function
            description: Feature description
            feature_type: Feature data type
            tags: Feature tags
            owner: Feature owner
            parameters: Feature parameters
            
        Returns:
            Created feature definition
        """
        metadata = {
            "description": description,
            "feature_type": feature_type,
            "tags": tags or [],
            "owner": owner,
            "parameters": parameters or {},
        }
        
        self.registry.register_computer(name, computer, metadata)
        
        # Return the created feature definition
        feature_def = self.storage.get_feature_definition(f"{name}_v1")
        if feature_def is None:
            raise RuntimeError("Failed to create feature definition")
        
        return feature_def
    
    def compute_feature(
        self,
        feature_name: str,
        data: pd.DataFrame,
        entity_col: str,
        timestamp_col: str,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Compute feature values.
        
        Args:
            feature_name: Name of feature to compute
            data: Input data
            entity_col: Entity identifier column
            timestamp_col: Timestamp column
            **kwargs: Additional parameters
            
        Returns:
            DataFrame with computed feature values
        """
        computer = self.registry.get_computer(feature_name)
        if computer is None:
            raise ValueError(f"Feature '{feature_name}' not found")
        
        logger.info(f"Computing feature: {feature_name}")
        
        # Validate input data
        required_cols = [entity_col, timestamp_col]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Compute feature
        try:
            result = computer(data, entity_col, timestamp_col, **kwargs)
            
            # Ensure result is indexed by entity
            if entity_col in result.columns:
                result = result.set_index(entity_col)
            
            logger.info(f"Computed {len(result)} feature values for {feature_name}")
            return result
            
        except Exception as e:
            logger.error(f"Error computing feature {feature_name}: {e}")
            raise
    
    def store_feature(
        self,
        feature_name: str,
        values: pd.DataFrame,
        metadata: Optional[Dict[str, Any]] = None,
        validate_schema: bool = True,
        dry_run: bool = False,
    ) -> ValidationResult:
        """Store computed feature values.
        
        Args:
            feature_name: Feature name
            values: Feature values to store
            metadata: Additional metadata
            validate_schema: Whether to validate schema before storing
            dry_run: If True, validate but don't store
            
        Returns:
            ValidationResult if validate_schema=True, otherwise empty ValidationResult
        """
        # Get feature definition
        feature_def = self.storage.get_feature_definition(f"{feature_name}_v1")
        if feature_def is None:
            raise ValueError(f"Feature '{feature_name}' not found")
        
        # Validate schema if requested
        if validate_schema:
            result = dry_run_ingestion(values, FEATURE_VALUE_SCHEMA, log_issues=True)
            if not result.is_valid and not dry_run:
                logger.error("Schema validation failed, not storing feature")
                return result
        else:
            result = ValidationResult(is_valid=True)
        
        # Store values if not dry run
        if not dry_run:
            self.storage.store_feature_values(feature_def.feature_id, values, metadata)
            # Update cache
            self._cache[feature_def.feature_id] = values
            logger.info(f"Stored feature '{feature_name}' with {len(values)} values")
        else:
            logger.info(f"Dry run: would store feature '{feature_name}' with {len(values)} values")
        
        return result
    
    @cache_feature_store(ttl_seconds=900)
    def get_feature(
        self,
        feature_name: str,
        entity_ids: Optional[List[str]] = None,
        timestamp: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> Optional[pd.DataFrame]:
        """Retrieve stored feature values.
        
        Args:
            feature_name: Feature name
            entity_ids: Optional entity IDs to filter
            timestamp: Optional timestamp for point-in-time queries
            use_cache: Whether to use cached values
            
        Returns:
            Feature values if found, None otherwise
        """
        feature_def = self.storage.get_feature_definition(f"{feature_name}_v1")
        if feature_def is None:
            raise ValueError(f"Feature '{feature_name}' not found")
        
        # Check cache first
        if use_cache and feature_def.feature_id in self._cache:
            values = self._cache[feature_def.feature_id].copy()
            
            if entity_ids:
                values = values[values.index.isin(entity_ids)]
            
            return values
        
        # Load from storage
        values = self.storage.get_feature_values(feature_def.feature_id, entity_ids, timestamp)
        
        if values is not None and use_cache:
            self._cache[feature_def.feature_id] = values.copy()
        
        return values
    
    def compute_and_store(
        self,
        feature_name: str,
        data: pd.DataFrame,
        entity_col: str,
        timestamp_col: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Compute and store feature values in one step.
        
        Args:
            feature_name: Feature name
            data: Input data
            entity_col: Entity identifier column
            timestamp_col: Timestamp column
            metadata: Additional metadata
            **kwargs: Additional parameters
            
        Returns:
            Computed feature values
        """
        values = self.compute_feature(feature_name, data, entity_col, timestamp_col, **kwargs)
        self.store_feature(feature_name, values, metadata)
        return values
    
    def create_feature_set(
        self,
        name: str,
        feature_names: List[str],
        description: str,
        entity_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FeatureSet:
        """Create a feature set.
        
        Args:
            name: Feature set name
            feature_names: List of feature names
            description: Feature set description
            entity_type: Entity type
            metadata: Additional metadata
            
        Returns:
            Created feature set
        """
        # Get feature IDs
        feature_ids = []
        for feature_name in feature_names:
            feature_def = self.storage.get_feature_definition(f"{feature_name}_v1")
            if feature_def is None:
                raise ValueError(f"Feature '{feature_name}' not found")
            feature_ids.append(feature_def.feature_id)
        
        feature_set = FeatureSet(
            name=name,
            description=description,
            feature_ids=feature_ids,
            entity_type=entity_type,
            metadata=metadata or {},
        )
        
        self.storage.store_feature_set(feature_set)
        return feature_set
    
    def get_feature_set(self, name: str) -> Optional[FeatureSet]:
        """Retrieve feature set.
        
        Args:
            name: Feature set name
            
        Returns:
            Feature set if found, None otherwise
        """
        return self.storage.get_feature_set(name)
    
    def get_features_for_entities(
        self,
        feature_names: List[str],
        entity_ids: List[str],
        timestamp: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """Get multiple features for specific entities.
        
        Args:
            feature_names: List of feature names
            entity_ids: List of entity IDs
            timestamp: Optional timestamp for point-in-time queries
            
        Returns:
            DataFrame with features indexed by entity
        """
        feature_data = {}
        
        for feature_name in feature_names:
            values = self.get_feature(feature_name, entity_ids, timestamp)
            if values is not None:
                # Extract the feature column (assuming single column features)
                if len(values.columns) == 1:
                    feature_data[feature_name] = values.iloc[:, 0]
                else:
                    # Multi-column features - prefix column names
                    for col in values.columns:
                        feature_data[f"{feature_name}_{col}"] = values[col]
        
        if not feature_data:
            return pd.DataFrame()
        
        result = pd.DataFrame(feature_data, index=entity_ids)
        return result
    
    def list_features(
        self,
        status: Optional[FeatureStatus] = None,
        tags: Optional[List[str]] = None,
        owner: Optional[str] = None,
    ) -> List[FeatureDefinition]:
        """List available features.
        
        Args:
            status: Filter by status
            tags: Filter by tags
            owner: Filter by owner
            
        Returns:
            List of feature definitions
        """
        return self.storage.list_feature_definitions(status, tags, owner)
    
    def clear_cache(self) -> None:
        """Clear feature cache."""
        self._cache.clear()
        logger.info("Feature cache cleared")
    
    @contextmanager
    def batch_mode(self):
        """Context manager for batch operations."""
        # Clear cache at start of batch
        self.clear_cache()
        try:
            yield
        finally:
            # Clear cache at end of batch
            self.clear_cache()


# Convenience functions

def create_feature_store(storage_path: str = "./feature_store") -> FeatureStore:
    """Create a feature store instance.
    
    Args:
        storage_path: Path to feature store storage
        
    Returns:
        Feature store instance
    """
    return FeatureStore(storage_path)


def get_feature_store(storage_path: str = "./feature_store") -> FeatureStore:
    """Get existing feature store instance.
    
    Args:
        storage_path: Path to feature store storage
        
    Returns:
        Feature store instance
    """
    return FeatureStore(storage_path)
