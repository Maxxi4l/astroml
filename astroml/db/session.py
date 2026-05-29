"""Database session factory for AstroML.

Resolves the database URL from (in priority order):
1. ``ASTROML_DATABASE_URL`` environment variable
2. ``config/database.yaml``
3. Fallback default: ``postgresql://astroml:@localhost:5432/astroml``
"""
from __future__ import annotations

import os
import pathlib
from functools import lru_cache
from typing import Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseConfig(BaseModel):
    """Database configuration with validation."""
    
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    name: str = Field(default="astroml", min_length=1, description="Database name")
    user: str = Field(default="astroml", min_length=1, description="Database user")
    password: str = Field(default="", description="Database password")
    
    @field_validator("host")
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate host is not empty."""
        if not v or not v.strip():
            raise ValueError("Database host cannot be empty")
        return v.strip()
    
    def to_url(self) -> str:
        """Convert configuration to PostgreSQL URL."""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
    
    @classmethod
    def from_dict(cls, data: dict) -> "DatabaseConfig":
        """Create configuration from dictionary with validation."""
        return cls(**data)


def load_database_config(config_path: Optional[pathlib.Path] = None) -> DatabaseConfig:
    """Load and validate database configuration from YAML file.
    
    Args:
        config_path: Path to database.yaml. Defaults to config/database.yaml.
        
    Returns:
        Validated DatabaseConfig instance.
        
    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValidationError: If config is invalid.
    """
    if config_path is None:
        config_path = pathlib.Path("config/database.yaml")
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Database config file not found at {config_path}. "
            f"Please create it or set ASTROML_DATABASE_URL environment variable."
        )
    
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    
    db_data = cfg.get("database", {})
    
    try:
        return DatabaseConfig.from_dict(db_data)
    except ValidationError as e:
        raise ValidationError(
            f"Invalid database configuration in {config_path}:\n{e}"
        ) from e


def resolve_database_url() -> str:
    """Return the database URL, preferring env var over config file."""
    env_url = os.environ.get("ASTROML_DATABASE_URL")
    if env_url:
        return env_url

    try:
        config = load_database_config()
        return config.to_url()
    except FileNotFoundError:
        # Fall back to default if config doesn't exist
        return "postgresql://astroml:@localhost:5432/astroml"
    except ValidationError as e:
        # Re-raise validation errors with clear message
        raise ValueError(
            f"Database configuration error: {e}\n"
            f"Please fix config/database.yaml or set ASTROML_DATABASE_URL environment variable."
        ) from e


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return a cached SQLAlchemy engine."""
    return create_engine(resolve_database_url(), pool_pre_ping=True)


def get_session() -> Session:
    """Return a new SQLAlchemy session."""
    factory = sessionmaker(bind=get_engine())
    return factory()
