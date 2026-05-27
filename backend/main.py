from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.src.services.claims_service import (
    ask_agent,
    cities_ranking,
    dashboard_summary,
    executive_report,
    get_claim,
    list_claims,
    providers_ranking,
    top_risk,
)


app = FastAPI(
    title="CheckIA API",
    description="API para revision asistida de posibles riesgos en siniestros sinteticos.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgentRequest(BaseModel):
    message: str


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": "CheckIA", "message": "API operativa con datos sinteticos"}


@app.get("/api/claims")
def claims() -> list[dict]:
    return list_claims()


@app.get("/api/claims/{claim_id}")
def claim_detail(claim_id: str) -> dict:
    claim = get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado")
    return claim


@app.get("/api/dashboard/summary")
def summary() -> dict:
    return dashboard_summary()


@app.get("/api/risk/top")
def risk_top(limit: int = 10) -> list[dict]:
    return top_risk(limit)


@app.get("/api/providers/ranking")
def provider_ranking() -> list[dict]:
    return providers_ranking()


@app.get("/api/cities/ranking")
def city_ranking() -> list[dict]:
    return cities_ranking()


@app.get("/api/reports/executive-summary")
def report() -> dict:
    return executive_report()


@app.post("/api/agent/chat")
def agent_chat(request: AgentRequest) -> dict:
    return ask_agent(request.message)


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV para demostracion.")
    content = await file.read()
    return {
        "filename": file.filename,
        "size_bytes": len(content),
        "message": "Archivo recibido. En esta demo se mantienen activos los datos sinteticos precargados.",
    }
