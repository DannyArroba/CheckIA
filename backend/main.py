from __future__ import annotations

import platform
import shutil
import subprocess
import sys
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
    hackia_executive_report,
    hackia_model_status,
    hackia_pdf_path,
    hackia_summary,
    hackia_tables,
    hackia_uploaded_pdfs,
    import_excel_workbook,
    ocr_runtime_status,
    process_pdf_batch,
    recalculate_hackia_analysis,
)
from backend.src.services.claims_service import (
    ask_agent,
    agent_status,
    cities_ranking,
    dashboard_summary,
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


def _legacy_shape_claim(row: dict) -> dict:
    level = row.get("nivel_riesgo") or "Bajo"
    return {
        "claim_id": row.get("id_siniestro"),
        "anonymous_customer": row.get("asegurado_nombre") or row.get("id_asegurado") or "Asegurado anonimo",
        "line": row.get("ramo") or "Sin ramo",
        "coverage": row.get("cobertura") or "Sin cobertura",
        "city": row.get("ciudad") or row.get("sucursal") or "Sin ciudad",
        "provider_name": row.get("proveedor_nombre") or row.get("nombre_proveedor") or row.get("id_proveedor") or "Sin proveedor",
        "claim_amount": float(row.get("monto_reclamado") or 0),
        "risk_score": int(row.get("puntaje_riesgo") or 0),
        "risk_level": level,
        "risk_color": "Rojo" if level in {"Alto", "Critico"} else "Amarillo" if level == "Medio" else "Verde",
        "recommended_action": "Revision prioritaria por analista" if level in {"Alto", "Critico"} else "Revision documental recomendada" if level == "Medio" else "Continuar flujo normal",
        "claim_date": row.get("fecha_siniestro"),
        "report_date": row.get("fecha_reporte"),
    }


def _legacy_shape_summary(summary_data: dict, rows: list[dict]) -> dict:
    distribution = [{"risk_level": item["nivel_riesgo"], "count": item["total"]} for item in summary_data.get("risk_distribution", [])]
    by_level = {item["risk_level"]: item["count"] for item in distribution}
    mapped = [_legacy_shape_claim(row) for row in rows]
    total_amount = sum(item["claim_amount"] for item in mapped)
    total_claims = summary_data.get("counts", {}).get("siniestros", len(rows))
    smart_summary = (
        f"Dataset HackIAthon activo con {total_claims} siniestros importados. Las alertas son apoyo para revision humana."
        if total_claims
        else "Aun no hay siniestros importados. Sube un Excel desde Datos para iniciar el analisis."
    )
    return {
        "total_claims": total_claims,
        "green_cases": by_level.get("Bajo", 0),
        "yellow_cases": by_level.get("Medio", 0),
        "red_cases": by_level.get("Alto", 0) + by_level.get("Critico", 0),
        "total_claim_amount": total_amount,
        "providers_with_alerts": len({row.get("id_proveedor") for row in rows if row.get("alertas") and row.get("id_proveedor")}),
        "risk_distribution": distribution,
        "top_claims": mapped[:10],
        "smart_summary": smart_summary,
    }


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": "CheckIA", "message": "API operativa"}


@app.get("/api/system/status")
def system_status() -> dict:
    node_version = None
    node_path = find_node_executable()
    if node_path:
        try:
            completed = subprocess.run([str(node_path), "--version"], capture_output=True, text=True, timeout=2, check=False)
            node_version = completed.stdout.strip() or None
        except Exception:
            node_version = None
    return {
        "api": {"ok": True, "name": "FastAPI", "python": sys.version.split()[0], "platform": platform.system()},
        "frontend": {"ok": True, "name": "Vite/React", "message": "Interfaz cargada en el navegador"},
        "node": {"ok": bool(node_version), "version": node_version, "path": node_path},
        "ocr": ocr_runtime_status(),
        "database": database_status(),
        "ollama": agent_status(),
        "hackia": hackia_summary(),
    }


def find_node_executable() -> Path | None:
    command = shutil.which("node")
    if command:
        return Path(command)
    candidates = [
        Path("/usr/bin/node"),
        Path("/usr/local/bin/node"),
        Path("/snap/bin/node"),
        Path("/root/.nvm/versions/node"),
    ]
    for path in candidates:
        if path.is_file():
            return path
        if path.is_dir():
            match = next(path.rglob("bin/node"), None)
            if match and match.exists():
                return match
    return None


@app.get("/api/claims")
def claims() -> list[dict]:
    return [_legacy_shape_claim(row) for row in hackia_claims()]


@app.get("/api/claims/{claim_id}")
def claim_detail(claim_id: str) -> dict:
    if claim_id.upper().startswith("SIN"):
        detail = hackia_claim_detail(claim_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Siniestro no encontrado")
        return detail
    claim = get_claim(claim_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Siniestro no encontrado")
    return claim


@app.get("/api/dashboard/summary")
def summary() -> dict:
    rows = hackia_claims()
    hackia = hackia_summary()
    if hackia.get("counts", {}).get("siniestros", 0) > 0:
        return _legacy_shape_summary(hackia, rows)
    return _legacy_shape_summary(hackia, [])


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
    return hackia_executive_report()


@app.get("/api/model/hybrid-status")
def model_hybrid_status() -> dict:
    hackia = hackia_summary()
    if hackia.get("counts", {}).get("siniestros", 0) > 0:
        return hackia_model_status()
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
    summary_data = hackia_summary()
    if summary_data.get("counts", {}).get("siniestros", 0) <= 0:
        raise HTTPException(status_code=400, detail="Primero sube el Excel con la hoja 1_Siniestros. Los PDFs se vinculan contra esos SIN/DOC.")
    incoming_dir = PDF_DIR / "_incoming"
    incoming_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            continue
        path = incoming_dir / Path(file.filename).name
        path.write_bytes(await file.read())
        paths.append(path)
    if not paths:
        raise HTTPException(status_code=400, detail="No se recibieron PDFs validos.")
    try:
        result = process_pdf_batch(paths)
        for path in paths:
            path.unlink(missing_ok=True)
        return result
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


@app.get("/api/hackia/pdfs")
def get_hackia_pdfs() -> list[dict]:
    try:
        return hackia_uploaded_pdfs()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo leer PDFs subidos: {exc}") from exc


@app.get("/api/hackia/pdfs/{id_documento}/download")
def download_hackia_pdf(id_documento: str) -> FileResponse:
    path = hackia_pdf_path(id_documento)
    if not path:
        raise HTTPException(status_code=404, detail="PDF no encontrado")
    return FileResponse(path, filename=path.name, media_type="application/pdf")


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
