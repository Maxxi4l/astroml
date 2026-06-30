from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def test_loyalty_recommendations_endpoint_returns_recommendations():
    response = client.post(
        "/api/v1/loyalty/recommendations",
        json={
            "account_id": "GA123",
            "balance": 1200,
            "transactions": [
                {"amount": 300, "asset": "XLM"},
                {"amount": 320, "asset": "XLM"},
                {"amount": 280, "asset": "XLM"},
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["account_id"] == "GA123"
    assert len(body["recommendations"]) >= 2
    assert body["response_time_ms"] < 2000
    assert sum(item["expected_acceptance_rate"] for item in body["recommendations"]) > 0


def test_sentiment_ingest_and_analysis_pipeline():
    ingest_response = client.post(
        "/api/v1/sentiment/ingest",
        json={
            "asset": "XLM",
            "items": [
                {"text": "Bullish breakout for XLM!", "timestamp": "2026-06-30T00:00:00+00:00"},
                {"text": "Market is weak and bearish", "timestamp": "2026-06-30T01:00:00+00:00"},
            ],
        },
    )
    assert ingest_response.status_code == 200
    analysis = client.get("/api/v1/sentiment/XLM/analysis")
    assert analysis.status_code == 200
    body = analysis.json()
    assert body["asset"] == "XLM"
    assert body["points"] >= 2

    series = client.get("/api/v1/sentiment/XLM/timeseries")
    assert series.status_code == 200
    series_body = series.json()
    assert series_body["asset"] == "XLM"
    assert len(series_body["points"]) >= 2
