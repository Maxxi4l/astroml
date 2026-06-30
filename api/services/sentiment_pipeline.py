from __future__ import annotations

import math
import time
from datetime import datetime, timedelta, timezone
from typing import Any


class SentimentAnalysisPipeline:
    """A lightweight sentiment pipeline with time-series tracking for Stellar assets."""

    def __init__(self) -> None:
        self._state: dict[str, list[dict[str, Any]]] = {}

    def ingest(self, asset: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        scores = []
        for item in items:
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            score = self._score_text(text)
            scores.append({"timestamp": item.get("timestamp") or datetime.now(timezone.utc).isoformat(), "score": score})

        if asset not in self._state:
            self._state[asset] = []
        self._state[asset].extend(scores)
        self._state[asset] = self._state[asset][-200:]
        return {"asset": asset, "ingested": len(scores), "latest_score": self._latest_score(asset)}

    def analyze(self, asset: str) -> dict[str, Any]:
        points = self._state.get(asset, [])
        if not points:
            return {"asset": asset, "sentiment_score": 0.0, "label": "neutral", "points": 0}

        avg = sum(item["score"] for item in points) / len(points)
        label = "positive" if avg > 0.2 else "negative" if avg < -0.2 else "neutral"
        return {"asset": asset, "sentiment_score": round(avg, 4), "label": label, "points": len(points)}

    def get_timeseries(self, asset: str, hours: int = 24) -> list[dict[str, Any]]:
        points = self._state.get(asset, [])
        if not points:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        series = []
        for item in points:
            ts = item.get("timestamp")
            if not ts:
                continue
            try:
                parsed = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            except ValueError:
                continue
            if parsed >= cutoff:
                series.append({"timestamp": parsed.isoformat(), "score": item["score"]})
        return series

    def get_visualization(self, asset: str) -> dict[str, Any]:
        series = self.get_timeseries(asset)
        if not series:
            return {"asset": asset, "points": [], "trend": "neutral"}
        scores = [item["score"] for item in series]
        avg = sum(scores) / len(scores)
        trend = "positive" if avg > 0.1 else "negative" if avg < -0.1 else "neutral"
        return {"asset": asset, "points": series[-24:], "trend": trend, "average_score": round(avg, 4)}

    def _latest_score(self, asset: str) -> float:
        if not self._state.get(asset):
            return 0.0
        return self._state[asset][-1]["score"]

    def _score_text(self, text: str) -> float:
        lowered = text.lower()
        positive_words = ["bullish", "up", "surge", "breakout", "buy", "optimistic", "strong", "adoption", "good"]
        negative_words = ["bearish", "down", "drop", "crash", "sell", "pessimistic", "weak", "risk", "bad"]
        score = 0.0
        for word in positive_words:
            if word in lowered:
                score += 0.25
        for word in negative_words:
            if word in lowered:
                score -= 0.25
        if any(token in lowered for token in ["!", "moon", "wow"]):
            score += 0.1
        if any(token in lowered for token in ["?", "uncertain", "unclear"]):
            score -= 0.1
        return max(-1.0, min(1.0, round(score, 3)))
