"""
Shared pytest fixtures for API integration tests.

Issue #264 — Integration tests for API endpoints and CI pipeline.

Provides:
  - `db_session`  : in-memory SQLite session (no Postgres needed in CI)
  - `sample_accounts`, `sample_transactions`, `sample_alerts`: seed data
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

# Import the ORM base so all models are registered
from astroml.db.schema import Base


# ─── Engine / session ─────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db_engine(tmp_path):
    """Ephemeral SQLite engine scoped to this test function (issue #204 pattern)."""
    db_file = tmp_path / "test_astroml.db"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})

    # Enable WAL mode for better concurrent-read performance in tests
    @event.listens_for(engine, "connect")
    def set_wal(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA journal_mode=WAL")

    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Session:
    """Clean session for each test — all writes are rolled back on teardown."""
    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


# ─── Seed data fixtures ───────────────────────────────────────────────────────

@pytest.fixture()
def sample_accounts():
    """Minimal account dicts for use as test data."""
    return [
        {"account_id": "GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN", "sequence": 1},
        {"account_id": "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPGZWXNBFNKKZ4YH67FQJG2FZT", "sequence": 2},
        {"account_id": "GCKFBEIYV2U22IO2BJ4KVJOIP7XPWQGQFKKWXR6DOSJBV5SG3B3ORJF", "sequence": 3},
    ]


@pytest.fixture()
def sample_transactions():
    """Minimal transaction dicts for use as test data."""
    return [
        {
            "transaction_hash": "abc123",
            "ledger_sequence": 100,
            "source_account": "GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN",
            "fee_charged": 100,
            "operation_count": 1,
            "successful": True,
        },
        {
            "transaction_hash": "def456",
            "ledger_sequence": 101,
            "source_account": "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPGZWXNBFNKKZ4YH67FQJG2FZT",
            "fee_charged": 200,
            "operation_count": 2,
            "successful": True,
        },
        {
            "transaction_hash": "ghi789",
            "ledger_sequence": 102,
            "source_account": "GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN",
            "fee_charged": 100,
            "operation_count": 1,
            "successful": False,
        },
    ]


@pytest.fixture()
def sample_alerts():
    """Minimal alert dicts for fraud/anomaly detection tests."""
    return [
        {"alert_id": "a1", "account_id": "GAAZI4TCR3TY5OJHCTJC2A4QSY6CJWJH5IAJTGKIN2ER7LBNVKOCCWN", "severity": "high", "resolved": False},
        {"alert_id": "a2", "account_id": "GBZXN7PIRZGNMHGA7MUUUF4GWPY5AYPGZWXNBFNKKZ4YH67FQJG2FZT", "severity": "low",  "resolved": True},
    ]
