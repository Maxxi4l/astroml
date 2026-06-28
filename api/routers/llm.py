import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.services.llm_explainer import TransactionExplainer
from api.services.llm_query import QueryTranslator
from api.services.llm_context import MultiModalContextHandler
from api.services.llm_validation import ResponseValidator
from api.services.llm_rag import build_citations, build_rag_answer, retrieve_sources
from astroml.llm.embedding_cache import EmbeddingCache
from astroml.llm.embedding_drift import EmbeddingDriftMonitor
from astroml.llm.memory import ConversationMemory
from astroml.llm.provider import MockLLMProvider
from astroml.llm.providers.embedding_router import build_default_router
from api.database import get_db
from api.models.orm import LLMFeedback
from api.schemas import (
    LLMFeedbackDashboard,
    LLMFeedbackIn,
    LLMFeedbackOut,
    LLMFeedbackTrend,
    LLMPromptImprovement,
)
from api.auth.dependencies import get_current_auth, AuthContext
from typing import List, Dict, Any, AsyncGenerator

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
async def explain_transaction(request: ExplainRequest, auth: AuthContext = Depends(get_current_auth)):
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
async def translate_query(request: QueryRequest, auth: AuthContext = Depends(get_current_auth)):
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
async def get_multimodal_context(request: ContextRequest, auth: AuthContext = Depends(get_current_auth)):
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
async def validate_response(request: ValidateRequest, auth: AuthContext = Depends(get_current_auth)):
    try:
        validated = validator.validate_and_guard(request.raw_response, request.context)
        return ValidateResponse(validated_response=validated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class AskRequest(BaseModel):
    question: str


class CitationResponse(BaseModel):
    source_id: str
    title: str
    url: str
    snippet: str


class AskResponse(BaseModel):
    answer: str
    citations: List[CitationResponse]
    mode: str


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest, auth: AuthContext = Depends(get_current_auth)):
    try:
        sources = retrieve_sources(request.question)
        citations = build_citations(request.question, sources)
        return AskResponse(
            answer=build_rag_answer(request.question, citations),
            citations=[CitationResponse(**citation.__dict__) for citation in citations],
            mode="mock-rag",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class StreamRequest(BaseModel):
    prompt: str


async def generate_stream_response(prompt: str) -> AsyncGenerator[str, None]:
    """Example streaming response generator."""
    response_chunks = [
        "This is",
        " a streaming",
        " response",
        " from the",
        " LLM service."
    ]
    for chunk in response_chunks:
        yield chunk + "\n"
        import asyncio
        await asyncio.sleep(0.1)


@router.post("/stream")
async def stream_response(request: StreamRequest, auth: AuthContext = Depends(get_current_auth)):
    """Streaming endpoint for LLM responses."""
    return StreamingResponse(
        generate_stream_response(request.prompt),
        media_type="text/plain"
    )


# Feedback collection for LLM outputs (#402)
@router.post("/feedback", response_model=LLMFeedbackOut, status_code=201)
async def submit_llm_feedback(
    payload: LLMFeedbackIn,
    db: AsyncSession = Depends(get_db),
) -> LLMFeedback:
    """Collect one-click/user or weighted expert feedback for an LLM output."""
    weight = payload.expert_weight if payload.is_expert else 1.0
    feedback = LLMFeedback(
        feature=payload.feature,
        prompt=payload.prompt,
        output=payload.output,
        rating=payload.rating,
        comment=payload.comment,
        user_id=payload.user_id,
        is_expert=payload.is_expert,
        expert_weight=weight,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    return feedback


@router.get("/feedback/dashboard", response_model=LLMFeedbackDashboard)
async def llm_feedback_dashboard(db: AsyncSession = Depends(get_db)) -> LLMFeedbackDashboard:
    """Return trend metrics used by the LLM feedback dashboard."""
    rows = (await db.execute(select(LLMFeedback))).scalars().all()
    grouped: dict[str, list[LLMFeedback]] = {}
    for row in rows:
        grouped.setdefault(row.feature, []).append(row)

    trends = []
    for feature, items in sorted(grouped.items()):
        count = len(items)
        avg = sum(item.rating for item in items) / count
        weight_total = sum(item.expert_weight for item in items)
        weighted = sum(item.rating * item.expert_weight for item in items) / weight_total
        trends.append(
            LLMFeedbackTrend(
                feature=feature,
                count=count,
                average_rating=round(avg, 2),
                weighted_average_rating=round(weighted, 2),
                expert_count=sum(1 for item in items if item.is_expert),
            )
        )

    low_examples = sorted(rows, key=lambda item: (item.rating, -item.id))[:5]
    return LLMFeedbackDashboard(
        total=len(rows),
        trends=trends,
        low_rating_examples=[LLMFeedbackOut.model_validate(item) for item in low_examples],
    )


@router.get("/feedback/prompt-improvements", response_model=list[LLMPromptImprovement])
async def llm_prompt_improvements(db: AsyncSession = Depends(get_db)) -> list[LLMPromptImprovement]:
    """Summarize feedback into prompt-improvement recommendations."""
    low_rows = (
        await db.execute(select(LLMFeedback).where(LLMFeedback.rating <= 3))
    ).scalars().all()
    by_feature: dict[str, list[LLMFeedback]] = {}
    for row in low_rows:
        by_feature.setdefault(row.feature, []).append(row)

    return [
        LLMPromptImprovement(
            feature=feature,
            evidence_count=len(items),
            recommendation=(
                "Revise the prompt to request concise, cited, schema-valid output; "
                "prioritize expert comments when available."
            ),
        )
        for feature, items in sorted(by_feature.items())
    ]
