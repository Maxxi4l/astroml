from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.services.llm_explainer import TransactionExplainer

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])
explainer = TransactionExplainer()

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
