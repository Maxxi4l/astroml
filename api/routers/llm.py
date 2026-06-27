import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.services.llm_explainer import TransactionExplainer
from api.services.llm_query import QueryTranslator
from api.services.llm_context import MultiModalContextHandler
from api.services.llm_validation import ResponseValidator
from astroml.llm.memory import ConversationMemory
from astroml.llm.provider import MockLLMProvider
from astroml.llm.embedding_cache import EmbeddingCache
from astroml.llm.embedding_drift import EmbeddingDriftMonitor
from astroml.llm.providers.embedding_router import build_default_router
from typing import List, Dict, Any, Optional

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])
explainer = TransactionExplainer()
query_translator = QueryTranslator()
context_handler = MultiModalContextHandler()
validator = ResponseValidator()
memory = ConversationMemory()
llm_provider = MockLLMProvider()
embedding_cache = EmbeddingCache()
embedding_router = build_default_router()

# Drift monitor — dimension inferred lazily from first observed vector.
# Default to 384 (HuggingFace MiniLM-L6-v2 fallback dim); reconfigured at
# runtime if the active provider returns a different dimension.
_DRIFT_MONITOR_DIM = int(os.getenv("EMBEDDING_DRIFT_DIM", "384"))
drift_monitor = EmbeddingDriftMonitor(
    n_dims=_DRIFT_MONITOR_DIM,
    provider_name="default",
    check_every=50,
)




class ExplainRequest(BaseModel):
    tx_details: str

class ExplainResponse(BaseModel):
    explanation: str

@router.post("/explain", response_model=ExplainResponse)
async def explain_transaction(request: ExplainRequest):
    try:
        explanation = await explainer.explain(request.tx_details)
        return ExplainResponse(explanation=explanation)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    sql: str

@router.post("/query", response_model=QueryResponse)
async def translate_query(request: QueryRequest):
    try:
        sql = query_translator.translate_to_sql(request.query)
        return QueryResponse(sql=sql)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ContextRequest(BaseModel):
    edges: List[Dict[str, Any]] = []
    data_points: List[float] = []

class ContextResponse(BaseModel):
    graph_summary: str
    time_series_trend: str
    mermaid: str

@router.post("/context", response_model=ContextResponse)
async def get_multimodal_context(request: ContextRequest):
    try:
        summary = context_handler.serialize_and_summarize_graph(request.edges)
        trend = context_handler.extract_time_series(request.data_points)
        mermaid = context_handler.generate_mermaid_diagram([], request.edges)
        return ContextResponse(
            graph_summary=summary,
            time_series_trend=trend,
            mermaid=mermaid
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ValidateRequest(BaseModel):
    raw_response: Dict[str, Any]
    context: str

class ValidateResponse(BaseModel):
    validated_response: Dict[str, Any]

@router.post("/validate", response_model=ValidateResponse)
async def validate_response(request: ValidateRequest):
    try:
        validated = validator.validate_and_guard(request.raw_response, request.context)
        return ValidateResponse(validated_response=validated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Session management schemas
# ---------------------------------------------------------------------------

class CreateSessionResponse(BaseModel):
    session_id: str
    created_at: str


class SessionInfoResponse(BaseModel):
    id: str
    created_at: str
    turn_count: int
    is_summarized: bool


# ---------------------------------------------------------------------------
# Session management endpoints
# ---------------------------------------------------------------------------

@router.post("/sessions", response_model=CreateSessionResponse, status_code=201)
async def create_session():
    meta = memory.create_session()
    return CreateSessionResponse(session_id=meta["id"], created_at=meta["created_at"])


@router.get("/sessions/{session_id}", response_model=SessionInfoResponse)
async def get_session(session_id: str):
    meta = memory.get_session(session_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionInfoResponse(
        id=meta["id"],
        created_at=meta["created_at"],
        turn_count=meta["turn_count"],
        is_summarized=meta["is_summarized"],
    )


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    memory.delete_session(session_id)
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Multi-turn chat schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    response: str
    turn_count: int


# ---------------------------------------------------------------------------
# Multi-turn chat endpoint
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Multi-turn chat endpoint with full conversation memory (R3, R5/AC5.4)."""
    session_id = request.session_id
    message = request.message

    # 1. Load session metadata — 404 if the session doesn't exist (AC3.5).
    session = memory.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Load conversation history.
    history = memory.get_messages(session_id)

    # 3. Append the new user message.
    memory.add_message(session_id, "user", message)

    # 4. Build a plain-text prompt from the history + new user message.
    history_lines = "\n".join(
        f"{msg['role']}: {msg['content']}" for msg in history
    )
    prompt = (
        f"Conversation history:\n{history_lines}\n\n"
        f"User: {message}\nAssistant:"
    )

    # 5. Generate the assistant response synchronously.
    response_text = llm_provider.generate(prompt)

    # 6. Append the assistant response.
    memory.add_message(session_id, "assistant", response_text)

    # 7. Re-fetch metadata to get the updated turn_count.
    updated_session = memory.get_session(session_id)
    turn_count = updated_session["turn_count"] if updated_session else 0

    # 8. Trigger consolidation every 20 turns (AC5.4).
    if turn_count % 20 == 0 and turn_count > 0:
        memory.consolidate(session_id)

    # 9. Return the chat response (AC3.4).
    return ChatResponse(
        session_id=session_id,
        response=response_text,
        turn_count=turn_count,
    )


# ---------------------------------------------------------------------------
# Embedding cache — schemas
# ---------------------------------------------------------------------------

class EmbeddingCacheStoreRequest(BaseModel):
    text: str
    result: Any


class EmbeddingCacheLookupRequest(BaseModel):
    text: str


class EmbeddingCacheInvalidateRequest(BaseModel):
    text: str


class EmbeddingCacheStatsResponse(BaseModel):
    hits: int
    misses: int
    sets: int
    invalidations: int
    hit_rate: float


# ---------------------------------------------------------------------------
# Embedding cache — endpoints
# ---------------------------------------------------------------------------

@router.post("/embedding-cache/store", status_code=201)
async def store_embedding(request: EmbeddingCacheStoreRequest):
    """Store a text → result pair in the semantic embedding cache."""
    try:
        embedding_cache.store(text=request.text, result=request.result)
        return {"stored": True, "text_preview": request.text[:80]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embedding-cache/lookup")
async def lookup_embedding(request: EmbeddingCacheLookupRequest):
    """Look up a semantically similar cached result for *text*.

    Returns the cached result on a hit, or ``{"hit": false}`` on a miss.
    Lookup overhead is < 10 ms for up to 1 024 cached entries.
    """
    try:
        result = embedding_cache.get(text=request.text)
        if result is not None:
            return {"hit": True, "result": result}
        return {"hit": False, "result": None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/embedding-cache/stats", response_model=EmbeddingCacheStatsResponse)
async def get_embedding_cache_stats():
    """Return current cache hit/miss counts and hit rate (target > 30%)."""
    stats = embedding_cache.get_stats()
    return EmbeddingCacheStatsResponse(**stats)


@router.delete("/embedding-cache")
async def invalidate_all_embeddings():
    """Invalidate (clear) the entire embedding cache."""
    count = embedding_cache.invalidate_all()
    return {"invalidated": count}


@router.delete("/embedding-cache/entry")
async def invalidate_embedding(request: EmbeddingCacheInvalidateRequest):
    """Invalidate the cache entry for a specific text (exact match)."""
    existed = embedding_cache.invalidate(text=request.text)
    return {"invalidated": existed}


# ---------------------------------------------------------------------------
# Multi-embedding-model — schemas
# ---------------------------------------------------------------------------

class EmbedRequest(BaseModel):
    text: str
    use_cache: bool = True


class EmbedBatchRequest(BaseModel):
    texts: List[str]
    use_cache: bool = False


class EmbedResponse(BaseModel):
    text: str
    vector: List[float]
    dim: int
    provider: str
    cached: bool


class EmbedBatchResponse(BaseModel):
    results: List[EmbedResponse]


class EmbeddingProviderStatus(BaseModel):
    name: str
    output_dim: int
    available: bool
    active: bool


# ---------------------------------------------------------------------------
# Multi-embedding-model — endpoints
# ---------------------------------------------------------------------------

@router.post("/embeddings", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    """Embed a single text using the configured provider chain.

    Tries OpenAI → Cohere → HuggingFace → Local in order, falling back
    automatically within 500 ms.  Results are stored in the semantic
    embedding cache when ``use_cache=true``.
    """
    from astroml.llm.providers.embedding_base import EmbeddingError

    # Check cache first (exact + semantic match).
    cached_result = None
    if request.use_cache:
        cached_result = embedding_cache.get(request.text)
    if cached_result is not None and isinstance(cached_result, list):
        return EmbedResponse(
            text=request.text,
            vector=cached_result,
            dim=len(cached_result),
            provider="cache",
            cached=True,
        )

    try:
        vector = embedding_router.embed(request.text)
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    provider_name = (
        embedding_router.active_provider.name
        if embedding_router.active_provider
        else "unknown"
    )

    if request.use_cache:
        embedding_cache.store(request.text, vector)

    # Feed the vector into the drift monitor (silently ignores dim mismatch).
    drift_monitor.observe(vector)

    return EmbedResponse(
        text=request.text,
        vector=vector,
        dim=len(vector),
        provider=provider_name,
        cached=False,
    )


@router.post("/embeddings/batch", response_model=EmbedBatchResponse)
async def embed_batch(request: EmbedBatchRequest):
    """Embed a list of texts using the configured provider chain."""
    from astroml.llm.providers.embedding_base import EmbeddingError

    if not request.texts:
        return EmbedBatchResponse(results=[])

    try:
        vectors = embedding_router.embed_batch(request.texts)
    except EmbeddingError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    provider_name = (
        embedding_router.active_provider.name
        if embedding_router.active_provider
        else "unknown"
    )

    results = []
    for text, vector in zip(request.texts, vectors):
        if request.use_cache:
            embedding_cache.store(text, vector)
        results.append(EmbedResponse(
            text=text,
            vector=vector,
            dim=len(vector),
            provider=provider_name,
            cached=False,
        ))

    return EmbedBatchResponse(results=results)


@router.get("/embeddings/providers", response_model=List[EmbeddingProviderStatus])
async def get_embedding_providers():
    """Return availability status for all configured embedding providers."""
    return [EmbeddingProviderStatus(**s) for s in embedding_router.provider_status()]


# ---------------------------------------------------------------------------
# Embedding drift detection — schemas
# ---------------------------------------------------------------------------

class DriftObserveRequest(BaseModel):
    """Submit an embedding vector for drift tracking."""
    vector: List[float]
    provider_name: str = "unknown"


class DriftSummaryResponse(BaseModel):
    provider_name: str
    baseline_ready: bool
    n_observed: int
    drift_detected: bool
    drift_fraction: float
    mean_psi: float
    max_psi: float
    psi_level: str
    last_check: Optional[str]
    n_alerts: int


class DriftReportResponse(BaseModel):
    timestamp: str
    provider_name: str
    n_baseline_samples: int
    n_current_samples: int
    n_dims_checked: int
    n_dims_drifted: int
    drift_fraction: float
    drift_detected: bool
    mean_ks_statistic: float
    mean_psi: float
    max_psi: float
    psi_level: str


class AlertHistoryItem(BaseModel):
    timestamp: str
    provider_name: str
    drift_fraction: float
    mean_psi: float
    max_psi: float
    n_drifted_dims: int
    n_total_dims: int
    message: str


# ---------------------------------------------------------------------------
# Embedding drift detection — endpoints
# ---------------------------------------------------------------------------

@router.post("/embeddings/drift/observe", status_code=202)
async def drift_observe(request: DriftObserveRequest):
    """Submit an embedding vector to the drift tracker.

    Accepts any vector that matches the monitor's configured dimension.
    Returns 202 Accepted; drift checks run automatically every 50 observations.
    """
    drift_monitor.observe(request.vector)
    return {
        "accepted": True,
        "n_observed": drift_monitor.n_observed,
        "baseline_ready": drift_monitor.baseline_ready,
    }


@router.get("/embeddings/drift/summary", response_model=DriftSummaryResponse)
async def drift_summary():
    """Return a compact drift status summary for the active provider."""
    return DriftSummaryResponse(**drift_monitor.summary())


@router.post("/embeddings/drift/check", response_model=DriftReportResponse)
async def drift_check():
    """Trigger an immediate KS + PSI drift check and return the full report.

    Returns a report with ``drift_detected=False`` and zero dimensions
    checked when the baseline is not yet ready (< baseline_min_samples
    observations).
    """
    report = drift_monitor.check()
    return DriftReportResponse(
        timestamp=report.timestamp,
        provider_name=report.provider_name,
        n_baseline_samples=report.n_baseline_samples,
        n_current_samples=report.n_current_samples,
        n_dims_checked=report.n_dims_checked,
        n_dims_drifted=report.n_dims_drifted,
        drift_fraction=report.drift_fraction,
        drift_detected=report.drift_detected,
        mean_ks_statistic=report.mean_ks_statistic,
        mean_psi=report.mean_psi,
        max_psi=report.max_psi,
        psi_level=report.psi_level,
    )


@router.get("/embeddings/drift/alerts", response_model=List[AlertHistoryItem])
async def drift_alerts():
    """Return the history of drift alerts (most recent first, max 100)."""
    history = drift_monitor.get_alert_history()
    history.reverse()
    return [AlertHistoryItem(**a.to_dict()) for a in history]


@router.delete("/embeddings/drift/baseline")
async def drift_reset_baseline():
    """Reset the drift baseline so a new one is collected from scratch.

    Use this after intentionally switching embedding models or retraining,
    to avoid spurious drift alerts caused by the expected distribution shift.
    """
    drift_monitor.reset_baseline()
    return {"reset": True, "message": "Drift baseline cleared; re-establishing from new observations."}
