from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.src.services.database_service import (
    create_agent_conversation,
    database_status,
    delete_agent_conversation,
    delete_agent_message,
    get_claim_review_actions,
    list_agent_conversations,
    list_agent_messages,
    move_agent_message,
    rename_agent_conversation,
    save_claim_review_action,
)
from backend.src.services.dataset_service import append_uploaded_claims, generate_additional_claims
from backend.src.services.hackia_import_service import (
    EXCEL_DIR,
    PDF_DIR,
    clear_hackia_data,
    clear_legacy_demo_data,
    hackia_claim_detail,
    hackia_claims,
    hackia_summary,
    hackia_tables,
    import_excel_workbook,
    process_pdf_batch,
    recalculate_hackia_analysis,
)
from backend.src.services.claims_service import (
    ask_agent,
    agent_status,
    cities_ranking,
    dashboard_summary,
    executive_report,
    get_claim,
    hybrid_status,
    list_claims,
    providers_ranking,
    sync_database,
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
    conversation_id: int | None = None


class MoveMessageRequest(BaseModel):
    direction: str


class GenerateDatasetRequest(BaseModel):
    count: int = 25
    risk_mix: str = "balanceado"


class RenameConversationRequest(BaseModel):
    title: str


class ReviewActionRequest(BaseModel):
    status: str
    note: str | None = None


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


@app.get("/api/model/hybrid-status")
def model_hybrid_status() -> dict:
    return hybrid_status()


@app.post("/api/agent/chat")
def agent_chat(request: AgentRequest) -> dict:
    return ask_agent(request.message, request.conversation_id)


@app.get("/api/agent/status")
def get_agent_status() -> dict:
    return agent_status()


@app.get("/api/database/status")
def get_database_status() -> dict:
    return database_status()


@app.post("/api/database/sync")
def post_database_sync() -> dict:
    try:
        return sync_database()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo sincronizar MySQL: {exc}") from exc


@app.post("/api/agent/conversations")
def create_conversation() -> dict:
    conversation_id = create_agent_conversation()
    return {"conversation_id": conversation_id, "title": "Nuevo chat"}


@app.get("/api/agent/conversations")
def get_agent_conversations() -> list[dict]:
    try:
        return list_agent_conversations()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo leer conversaciones: {exc}") from exc


@app.patch("/api/agent/conversations/{conversation_id}")
def patch_agent_conversation(conversation_id: int, request: RenameConversationRequest) -> dict:
    rename_agent_conversation(conversation_id, request.title)
    return {"message": "Conversación renombrada"}


@app.delete("/api/agent/conversations/{conversation_id}")
def delete_conversation(conversation_id: int) -> dict:
    delete_agent_conversation(conversation_id)
    return {"message": "Conversación eliminada"}


@app.get("/api/agent/conversations/{conversation_id}/messages")
def get_agent_history(conversation_id: int) -> list[dict]:
    try:
        return list_agent_messages(conversation_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo leer historial: {exc}") from exc


@app.delete("/api/agent/history/{message_id}")
def delete_history_message(message_id: int) -> dict:
    delete_agent_message(message_id)
    return {"message": "Mensaje eliminado"}


@app.post("/api/agent/history/{message_id}/move")
def move_history_message(message_id: int, request: MoveMessageRequest) -> dict:
    if request.direction not in {"up", "down"}:
        raise HTTPException(status_code=400, detail="direction debe ser up o down")
    move_agent_message(message_id, request.direction)
    return {"message": "Mensaje reordenado"}


@app.post("/api/claims/{claim_id}/review-action")
def create_review_action(claim_id: str, request: ReviewActionRequest) -> dict:
    allowed = {"pendiente", "bajo_observacion", "documentacion_solicitada", "revisado_sin_alerta", "derivado_analista"}
    if request.status not in allowed:
        raise HTTPException(status_code=400, detail="Estado de revisión no permitido")
    return save_claim_review_action(claim_id, request.status, request.note)


@app.get("/api/claims/{claim_id}/review-actions")
def claim_review_actions(claim_id: str) -> list[dict]:
    return get_claim_review_actions(claim_id)


@app.post("/api/upload")
async def upload_dataset(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos CSV para demostracion.")
    content = await file.read()
    upload_dir = Path("backend/data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / file.filename
    path.write_bytes(content)
    result = append_uploaded_claims(path)
    if not result.get("accepted", False):
        raise HTTPException(status_code=400, detail=result)
    return {
        "filename": file.filename,
        "size_bytes": len(content),
        "message": "Archivo recibido y procesado. El modelo se recalcula con los datos actualizados.",
        "result": result,
    }


@app.post("/api/hackia/import-excel")
async def import_hackia_excel(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm", ".xls")):
        raise HTTPException(status_code=400, detail="Sube un archivo Excel con hojas 1_Siniestros a 6_Indice_Documentos.")
    EXCEL_DIR.mkdir(parents=True, exist_ok=True)
    path = EXCEL_DIR / Path(file.filename).name
    path.write_bytes(await file.read())
    try:
        return import_excel_workbook(path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/hackia/import-pdfs")
async def import_hackia_pdfs(files: list[UploadFile] = File(...)) -> dict:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            continue
        path = PDF_DIR / Path(file.filename).name
        path.write_bytes(await file.read())
        paths.append(path)
    if not paths:
        raise HTTPException(status_code=400, detail="No se recibieron PDFs validos.")
    try:
        return process_pdf_batch(paths)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudieron procesar PDFs: {exc}") from exc


@app.get("/api/hackia/summary")
def get_hackia_summary() -> dict:
    try:
        return hackia_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo leer resumen HackIAthon: {exc}") from exc


@app.get("/api/hackia/claims")
def get_hackia_claims() -> list[dict]:
    try:
        return hackia_claims()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo leer siniestros HackIAthon: {exc}") from exc


@app.get("/api/hackia/tables")
def get_hackia_tables() -> dict:
    try:
        return hackia_tables()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo leer tablas HackIAthon: {exc}") from exc


@app.get("/api/hackia/claims/{id_siniestro}")
def get_hackia_claim_detail(id_siniestro: str) -> dict:
    detail = hackia_claim_detail(id_siniestro)
    if not detail:
        raise HTTPException(status_code=404, detail="Siniestro HackIAthon no encontrado")
    return detail


@app.post("/api/hackia/recalculate")
def post_hackia_recalculate() -> dict:
    try:
        return recalculate_hackia_analysis()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo recalcular analisis: {exc}") from exc


@app.post("/api/hackia/clear-legacy")
def post_hackia_clear_legacy() -> dict:
    try:
        return clear_legacy_demo_data()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo limpiar datos anteriores: {exc}") from exc


@app.post("/api/hackia/clear")
def post_hackia_clear() -> dict:
    try:
        return clear_hackia_data()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo limpiar datos HackIAthon: {exc}") from exc


@app.post("/api/dataset/generate")
def generate_dataset(request: GenerateDatasetRequest) -> dict:
    if request.risk_mix not in {"balanceado", "alto"}:
        raise HTTPException(status_code=400, detail="risk_mix debe ser balanceado o alto")
    return generate_additional_claims(request.count, request.risk_mix)


@app.get("/api/dataset/download/{filename}")
def download_generated_dataset(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    path = Path("backend/data/generated") / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="CSV generado no encontrado")
    return FileResponse(path, filename=safe_name, media_type="text/csv")
