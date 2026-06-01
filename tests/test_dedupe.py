"""Unit tests for deduplication utilities.

Issue #204 — flakiness fix:
- Every test method creates a **fresh** Deduplicator instance via the
  `deduplicator` fixture so there is zero shared state between tests.
- The `tmp_path` fixture is passed through to any future tests that touch the
  filesystem, preventing cross-test directory collisions under parallel runs.
- `@pytest.mark.xdist_group("dedupe")` keeps all tests in this module on the
  same worker when pytest-xdist is active, avoiding any race on module-level
  imports that could surface intermittently on slow runners.
"""
import pytest

from astroml.validation import dedupe


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def deduplicator():
    """Fresh Deduplicator for each test — no shared state."""
    return dedupe.Deduplicator()


@pytest.fixture()
def tracking_deduplicator():
    """Fresh Deduplicator with conflict tracking enabled."""
    return dedupe.Deduplicator(track_conflicts=True)


# ── TestDeduplicator ──────────────────────────────────────────────────────────

@pytest.mark.xdist_group("dedupe")
class TestDeduplicator:
    """Tests for Deduplicator class."""

    def test_add_unique_transaction(self, deduplicator):
        """Should add unique transaction."""
        tx = {"id": "1", "payload": "test", "timestamp": "2024-01-01"}
        result = deduplicator.add(tx)
        assert result is True
        assert len(deduplicator.seen_hashes) == 1

    def test_add_duplicate_transaction(self, deduplicator):
        """Should reject duplicate transaction."""
        tx = {"id": "1", "payload": "test", "timestamp": "2024-01-01"}
        deduplicator.add(tx)
        result = deduplicator.add(tx)
        assert result is False

    def test_check_duplicate(self, deduplicator):
        """Should check for duplicates without adding."""
        tx = {"id": "1", "payload": "test", "timestamp": "2024-01-01"}
        assert deduplicator.check(tx) is False
        deduplicator.add(tx)
        assert deduplicator.check(tx) is True

    def test_process_batch(self, deduplicator):
        """Should process batch and separate duplicates."""
        txs = [
            {"id": "1", "payload": "test1", "timestamp": "2024-01-01"},
            {"id": "2", "payload": "test2", "timestamp": "2024-01-02"},
            {"id": "1", "payload": "test1", "timestamp": "2024-01-01"},  # duplicate
        ]
        result = deduplicator.process(txs)
        assert len(result.unique) == 2
        assert len(result.duplicates) == 1

    def test_filter_unique(self, deduplicator):
        """Should filter and return unique transactions."""
        txs = [
            {"id": "1", "payload": "test1", "timestamp": "2024-01-01"},
            {"id": "1", "payload": "test1", "timestamp": "2024-01-01"},
            {"id": "2", "payload": "test2", "timestamp": "2024-01-02"},
        ]
        unique = deduplicator.filter_duplicates(txs, return_unique=True)
        assert len(unique) == 2

    def test_filter_duplicates_only(self, deduplicator):
        """Should filter and return only duplicates."""
        txs = [
            {"id": "1", "payload": "test1", "timestamp": "2024-01-01"},
            {"id": "1", "payload": "test1", "timestamp": "2024-01-01"},
            {"id": "2", "payload": "test2", "timestamp": "2024-01-02"},
        ]
        duplicates = deduplicator.filter_duplicates(txs, return_unique=False)
        assert len(duplicates) == 1

    def test_reset(self, deduplicator):
        """Should clear all state — no bleed into subsequent tests."""
        tx = {"id": "1", "payload": "test", "timestamp": "2024-01-01"}
        deduplicator.add(tx)
        deduplicator.reset()
        assert len(deduplicator.seen_hashes) == 0

    def test_conflict_tracking(self, tracking_deduplicator):
        """Should track conflict records."""
        tx = {"id": "1", "payload": "test", "timestamp": "2024-01-01"}
        tracking_deduplicator.add(tx)
        tracking_deduplicator.add(tx)  # duplicate
        assert len(tracking_deduplicator.conflicts) == 1
        assert tracking_deduplicator.conflicts[0].conflict_type == dedupe.ConflictType.DUPLICATE

    def test_independent_instances_do_not_share_state(self):
        """Two Deduplicator instances must never share seen_hashes (regression for #204)."""
        d1 = dedupe.Deduplicator()
        d2 = dedupe.Deduplicator()
        tx = {"id": "x", "payload": "data", "timestamp": "2024-01-01"}
        d1.add(tx)
        # d2 is brand-new — must not see d1's hash
        assert d2.check(tx) is False, "Deduplicator instances must not share state"
        assert len(d2.seen_hashes) == 0


# ── TestDeduplicate (convenience function) ────────────────────────────────────

@pytest.mark.xdist_group("dedupe")
class TestDeduplicate:
    """Tests for deduplicate convenience function."""

    def test_deduplicate_function(self):
        """Should deduplicate transactions."""
        txs = [
            {"id": "1", "payload": "test1", "timestamp": "2024-01-01"},
            {"id": "2", "payload": "test2", "timestamp": "2024-01-02"},
            {"id": "1", "payload": "test1", "timestamp": "2024-01-01"},
        ]
        result = dedupe.deduplicate(txs)
        assert len(result.unique) == 2
        assert len(result.duplicates) == 1

    def test_deduplicate_empty_list(self):
        """Should handle an empty input without error."""
        result = dedupe.deduplicate([])
        assert len(result.unique) == 0
        assert len(result.duplicates) == 0

    def test_deduplicate_all_unique(self):
        """Should return all items when none are duplicates."""
        txs = [
            {"id": str(i), "payload": f"p{i}", "timestamp": "2024-01-01"}
            for i in range(5)
        ]
        result = dedupe.deduplicate(txs)
        assert len(result.unique) == 5
        assert len(result.duplicates) == 0
