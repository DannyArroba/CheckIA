from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import re

import pandas as pd

from backend.src.ai_agent.claims_agent import ClaimsAgent
from backend.src.ai_agent.ollama_client import OllamaClient
from backend.src.explainability.explain_score import explain_claim, risk_level
from backend.src.features.build_features import build_claim_contexts, build_model_features
from backend.src.ingestion.load_data import load_all_data
from backend.src.models.fraud_model import FraudRiskModel
from backend.src.services.database_service import (
    get_latest_review_actions,
    review_actions_summary,
    save_agent_message,
    sync_risk_results,
    sync_source_tables,
)


@lru_cache(maxsize=1)
def get_claims_dataset() -> pd.DataFrame:
    data = load_all_data()
    enriched = build_claim_contexts(data)
    features = build_model_features(enriched)
    model = FraudRiskModel()
    model.train_model(features)
    predictions = model.predict_risk(features)

    enriched = pd.concat([enriched.reset_index(drop=True), predictions.reset_index(drop=True)], axis=1)
    enriched["nlp_score"] = (enriched["similar_narrative_score"] * 100).round(2)
    enriched["risk_score"] = (
        enriched["rule_score"] * 0.70 + enriched["model_score"] * 0.20 + enriched["nlp_score"] * 0.10
    ).clip(0, 100).round(0).astype(int)
    enriched["risk_level"] = enriched["risk_score"].apply(lambda score: risk_level(score)["nivel"])
    enriched["risk_color"] = enriched["risk_score"].apply(lambda score: risk_level(score)["color"])
    enriched["recommended_action"] = enriched["risk_score"].apply(lambda score: risk_level(score)["accion"])
    enriched["explainability"] = enriched.apply(lambda row: explain_claim(row.to_dict()), axis=1)
    return enriched


def _clean_record(record: dict) -> dict:
    for key, value in list(record.items()):
        if isinstance(value, float) and pd.isna(value):
            record[key] = None
    return record


def _review_label(status: str | None) -> str:
    labels = {
        "pendiente": "Pendiente",
        "bajo_observacion": "Bajo observación",
        "documentacion_solicitada": "Documentación solicitada",
        "revisado_sin_alerta": "Revisado sin alerta adicional",
        "derivado_analista": "Derivado a analista",
    }
    return labels.get(status or "", "Sin seguimiento")


def _latest_reviews_for(claim_ids: list[str]) -> dict[str, dict]:
    try:
        return get_latest_review_actions(claim_ids)
    except Exception:
        return {}


def list_claims() -> list[dict]:
    df = get_claims_dataset().sort_values("risk_score", ascending=False)
    latest_reviews = _latest_reviews_for(df["claim_id"].tolist())
    columns = [
        "claim_id", "anonymous_customer", "line", "coverage", "city", "provider_name",
        "claim_amount", "risk_score", "risk_level", "risk_color", "recommended_action",
        "claim_date", "report_date",
    ]
    records = []
    for row in df[columns].to_dict(orient="records"):
        review = latest_reviews.get(row["claim_id"])
        row["review_status"] = review["status"] if review else None
        row["review_label"] = _review_label(row["review_status"])
        records.append(_clean_record(row))
    return records


def get_claim(claim_id: str) -> dict | None:
    df = get_claims_dataset()
    match = df[df["claim_id"] == claim_id]
    if match.empty:
        return None
    record = match.iloc[0].to_dict()
    review = _latest_reviews_for([claim_id]).get(claim_id)
    record["review_status"] = review["status"] if review else None
    record["review_label"] = _review_label(record["review_status"])
    record["review_note"] = review.get("note") if review else None
    return _clean_record(record)


def dashboard_summary() -> dict:
    df = get_claims_dataset()
    counts = df["risk_level"].value_counts().to_dict()
    top = df.nlargest(10, "risk_score")
    return {
        "total_claims": int(len(df)),
        "green_cases": int(counts.get("Bajo", 0)),
        "yellow_cases": int(counts.get("Medio", 0)),
        "red_cases": int(counts.get("Alto", 0)),
        "total_claim_amount": float(df["claim_amount"].sum()),
        "providers_with_alerts": int(df[df["risk_level"].isin(["Medio", "Alto"])]["provider_id"].nunique()),
        "risk_distribution": df.groupby("risk_level")["claim_id"].count().reset_index(name="count").to_dict(orient="records"),
        "top_claims": top[["claim_id", "anonymous_customer", "city", "provider_name", "claim_amount", "risk_score", "risk_level"]].to_dict(orient="records"),
        "smart_summary": ClaimsAgent(df).executive_summary(),
    }


def providers_ranking() -> list[dict]:
    df = get_claims_dataset()
    ranking = df.groupby("provider_name").agg(
        claims=("claim_id", "count"),
        alerts=("risk_level", lambda values: int(values.isin(["Medio", "Alto"]).sum())),
        avg_score=("risk_score", "mean"),
        total_amount=("claim_amount", "sum"),
    ).sort_values(["alerts", "avg_score"], ascending=False).reset_index()
    ranking["avg_score"] = ranking["avg_score"].round(1)
    return ranking.to_dict(orient="records")


def cities_ranking() -> list[dict]:
    df = get_claims_dataset()
    ranking = df.groupby("city").agg(
        claims=("claim_id", "count"),
        red_cases=("risk_level", lambda values: int((values == "Alto").sum())),
        avg_score=("risk_score", "mean"),
    ).sort_values(["red_cases", "avg_score"], ascending=False).reset_index()
    ranking["avg_score"] = ranking["avg_score"].round(1)
    return ranking.to_dict(orient="records")


def top_risk(limit: int = 10) -> list[dict]:
    df = get_claims_dataset().nlargest(limit, "risk_score")
    return df[["claim_id", "anonymous_customer", "line", "city", "provider_name", "claim_amount", "risk_score", "risk_level", "recommended_action"]].to_dict(orient="records")


def executive_report() -> dict:
    df = get_claims_dataset()
    agent = ClaimsAgent(df)
    rule_counts: dict[str, int] = {}
    for active_rules in df["rules"]:
        for rule in active_rules:
            rule_counts[rule["nombre"]] = rule_counts.get(rule["nombre"], 0) + 1
    signals = [{"signal": k, "count": v} for k, v in sorted(rule_counts.items(), key=lambda item: item[1], reverse=True)[:8]]
    return {
        "summary": agent.executive_summary(),
        "total_cases": int(len(df)),
        "critical_cases": int((df["risk_level"] == "Alto").sum()),
        "main_signals": signals,
        "providers": providers_ranking()[:5],
        "cities": cities_ranking()[:5],
        "recommendations": [
            "Priorizar revision humana de casos con score superior a 75.",
            "Validar documentos faltantes, ilegibles o inconsistentes antes de cualquier decision.",
            "Revisar concentraciones por proveedor y ciudad como patrones operativos, no como acusaciones.",
        ],
        "limitations": [
            "Datos sinteticos para demostracion.",
            "El score es una alerta de revision, no una decision legal ni contractual.",
            "Requiere gobierno de datos, auditoria y validacion con expertos antes de uso productivo.",
        ],
    }


def ask_agent(message: str, conversation_id: int | None = None) -> dict:
    conversation_id = save_agent_message("usuario", message, "usuario", conversation_id)
    quick_response = _light_ollama_response(message)
    if quick_response:
        save_agent_message("agente", quick_response["answer"], quick_response["provider"], conversation_id)
        quick_response["conversation_id"] = conversation_id
        return quick_response

    response = ClaimsAgent(get_claims_dataset(), _review_context()).answer(message)
    save_agent_message("agente", response["answer"], response.get("provider", "reglas"), conversation_id)
    response["conversation_id"] = conversation_id
    return response


def _light_ollama_response(message: str) -> dict | None:
    text = message.strip().lower()
    normalized = re.sub(r"[¿?¡!.,;:]+", "", text)
    simple_greetings = {
        "hola", "buenas", "hey", "holaa", "hello", "hi", "buenos dias", "buenos días",
        "buenas tardes", "buenas noches", "que tal", "qué tal"
    }
    wellbeing = {
        "como estas", "cómo estás", "como esta", "cómo está", "como vas", "cómo vas",
        "que haces", "qué haces", "todo bien", "como te va", "cómo te va"
    }
    thanks = {"gracias", "ok", "listo", "vale", "perfecto", "dale", "entendido", "ya"}

    if normalized in simple_greetings:
        return _ask_ollama_light(
            message,
            fallback="Hola. ¿Qué quieres revisar: casos críticos, proveedores, documentos o seguimientos?",
            suggestions=["Top 10 casos", "Proveedores con alertas", "Resumen ejecutivo"],
        )
    if normalized in wellbeing:
        return _ask_ollama_light(
            message,
            fallback="Estoy bien, listo para ayudarte con CheckIA. Si quieres, revisamos casos críticos o un resumen rápido.",
            suggestions=["Top 10 casos", "Resumen ejecutivo"],
        )
    if normalized in thanks:
        return _ask_ollama_light(
            message,
            fallback="Listo. Cuando quieras, seguimos revisando siniestros.",
            suggestions=["Top 10 casos", "Seguimiento humano"],
        )
    if normalized in {"que puedes hacer", "qué puedes hacer", "ayuda", "help", "ayudame", "ayúdame"}:
        return _ask_ollama_light(
            message,
            fallback="Puedo resumir riesgos, listar casos prioritarios, revisar proveedores, documentos, ciudades y seguimientos humanos.",
            suggestions=["Top 10 casos", "Documentos críticos", "Seguimiento humano"],
        )
    if not _has_claims_intent(normalized):
        return _ask_ollama_light(
            message,
            fallback="Sí, puedo ayudarte con eso. Si quieres, también puedo revisar información de siniestros.",
            suggestions=["Top 10 casos", "Resumen ejecutivo"],
        )
    return None


def _ask_ollama_light(message: str, fallback: str, suggestions: list[str]) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = (
        "El usuario hizo una interacción simple dentro de CheckIA. "
        "Responde con tono amable, natural y muy breve. "
        "No analices datos de siniestros, no menciones casos específicos y no inventes cifras. "
        f"Fecha actual del sistema: {today}. Si pregunta por la fecha o el día, responde usando esa fecha. "
        "No uses emojis. Máximo 25 palabras.\n\n"
        f"Mensaje del usuario: {message}"
    )
    answer = _clean_light_answer(_strip_symbols(OllamaClient().generate(prompt, num_predict=45, timeout=10) or fallback))
    return {
        "answer": answer,
        "related_claims": [],
        "provider": "ollama ligero",
        "suggestions": suggestions,
        "disclaimer": "",
    }


def _strip_symbols(text: str) -> str:
    return re.sub(r"[\U00010000-\U0010ffff]", "", text).strip()


def _clean_light_answer(text: str) -> str:
    blocked = [
        "CheckIA no puede tomar decisiones",
        "no puede tomar decisiones legales",
        "Recuerda que CheckIA",
        "Requiere análisis humano",
    ]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    kept = [line for line in lines if not any(phrase.lower() in line.lower() for phrase in blocked)]
    return " ".join(kept).strip() or text.strip()


def _has_claims_intent(text: str) -> bool:
    terms = [
        "caso", "casos", "siniestro", "siniestros", "riesgo", "riesgos", "fraude",
        "proveedor", "proveedores", "documento", "documentos", "monto", "montos",
        "ciudad", "ciudades", "seguimiento", "observacion", "observación", "estado",
        "poliza", "póliza", "reporte", "score", "alerta", "alertas", "resumen",
        "dashboard", "rojo", "amarillo", "verde", "top", "revisar", "revisión",
        "revision", "asegurado", "aseguradora", "cobertura", "claim", "clm-"
    ]
    return any(term in text for term in terms)


def _review_context() -> list[dict]:
    try:
        return review_actions_summary()
    except Exception:
        return []


def agent_status() -> dict:
    return OllamaClient().status()


def sync_database() -> dict:
    source_counts = sync_source_tables()
    risk_counts = sync_risk_results(get_claims_dataset())
    return {"source": source_counts, "risk": risk_counts}
