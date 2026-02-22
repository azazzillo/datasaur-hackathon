from fastapi import APIRouter, HTTPException, Request
# Local
from src.schemas import DiagnoseIn, DiagnoseOut
from src.core.config import settings
from src.services.diagnosis import diagnose_symptoms

router = APIRouter()


@router.post("/diagnose")
def diagnose(payload: DiagnoseIn, request: Request):
    retriever = request.app.state.retriever
    if retriever is None:
        raise HTTPException(status_code=503, detail="Retriever not initialized")

    return diagnose_symptoms(
        payload.symptoms,
        retriever=retriever,
        top_k=settings.top_k,
        icd_limit=settings.icd_limit,
        chunk_limit=settings.chunk_limit,
    )