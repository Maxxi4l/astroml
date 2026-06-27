from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.services.llm_explainer import TransactionExplainer
from api.services.llm_query import QueryTranslator
from api.services.llm_context import MultiModalContextHandler
from api.services.llm_validation import ResponseValidator
from api.services.llm_rag import build_citations, build_rag_answer, retrieve_sources
from typing import List, Dict, Any

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])
explainer = TransactionExplainer()
query_translator = QueryTranslator()
context_handler = MultiModalContextHandler()
validator = ResponseValidator()




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
async def ask_question(request: AskRequest):
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
