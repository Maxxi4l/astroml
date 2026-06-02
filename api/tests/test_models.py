"""Integration tests — model registry (issue #237)."""
from __future__ import annotations

import pytest
from pathlib import Path


@pytest.mark.xdist_group("api_models")
class TestModelRegistry:

    def test_list_models_empty(self, client):
        resp = client.get("/api/v1/models")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_register_model(self, client, tmp_path):
        src = tmp_path / "model.pth"
        src.write_bytes(b"fake-checkpoint")

        resp = client.post("/api/v1/models", json={
            "name": "gcn",
            "path": str(src),
            "metrics": {"auc": 0.95},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "gcn"
        assert data["status"] == "inactive"
        assert "gcn_v" in data["version"]
        assert data["metrics"]["auc"] == pytest.approx(0.95)

    def test_activate_model(self, client, tmp_path):
        src = tmp_path / "model.pth"
        src.write_bytes(b"fake-checkpoint")

        created = client.post("/api/v1/models", json={
            "name": "gcn",
            "path": str(src),
        }).json()

        resp = client.post(f"/api/v1/models/{created['id']}/activate")
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_model_metrics(self, client, tmp_path):
        src = tmp_path / "model.pth"
        src.write_bytes(b"fake-checkpoint")

        created = client.post("/api/v1/models", json={
            "name": "gcn",
            "path": str(src),
            "metrics": {"f1": 0.88},
        }).json()

        resp = client.get(f"/api/v1/models/{created['id']}/metrics")
        assert resp.status_code == 200
        assert resp.json()["metrics"]["f1"] == pytest.approx(0.88)

    def test_activate_not_found(self, client):
        resp = client.post("/api/v1/models/9999/activate")
        assert resp.status_code == 404
