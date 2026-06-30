from __future__ import annotations

from fastapi import APIRouter

from api.schemas import (
    SentimentAnalysisResponse,
    SentimentIngestRequest,
    SentimentSeriesResponse,
)
from api.services.sentiment_pipeline import SentimentAnalysisPipeline

router = APIRouter(prefix="/api/v1/sentiment", tags=["sentiment"])
pipeline = SentimentAnalysisPipeline()


@router.post("/ingest", response_model=dict)
def ingest_sentiment(payload: SentimentIngestRequest) -> dict:
    """Ingest social/news items for an asset and update the rolling sentiment state."""
    return pipeline.ingest(payload.asset, payload.items)


@router.get("/{asset}/analysis", response_model=SentimentAnalysisResponse)
def analyze_sentiment(asset: str) -> SentimentAnalysisResponse:
    """Return the current aggregate sentiment for an asset."""
    return pipeline.analyze(asset)


@router.get("/{asset}/timeseries", response_model=SentimentSeriesResponse)
def sentiment_timeseries(asset: str) -> SentimentSeriesResponse:
    """Return the recent time-series sentiment points used for visualization."""
    return pipeline.get_visualization(asset)
