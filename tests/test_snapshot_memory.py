from __future__ import annotations

from datetime import datetime, timezone

from astroml.features.graph.snapshot import Edge, iter_db_snapshots


class FakeResult:
    def __init__(self, rows):
        self._rows = rows
        self.yield_per_calls = 0

    def yield_per(self, size):
        self.yield_per_calls += 1
        assert size == 2
        return iter(self._rows)

    def all(self):
        raise AssertionError("iter_db_snapshots must stream rows in chunks")


class FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.execute_calls = 0

    def execute(self, _query):
        self.execute_calls += 1
        return FakeResult(self._rows)


def test_iter_db_snapshots_streams_in_chunks():
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    t_now = t0.replace(hour=1)
    rows = [
        type("Row", (), {"sender": "a", "receiver": "b", "timestamp": t0})(),
        type("Row", (), {"sender": "c", "receiver": "d", "timestamp": t0.replace(minute=1)})(),
    ]

    session = FakeSession(rows)

    windows = list(iter_db_snapshots("1h", t0=t0, t_now=t_now, session=session, chunk_size=2))

    assert len(windows) == 1
    assert windows[0].edges == [
        Edge(src="a", dst="b", timestamp=int(t0.timestamp())),
        Edge(src="c", dst="d", timestamp=int(t0.replace(minute=1).timestamp())),
    ]
    assert session.execute_calls == 1
