from __future__ import annotations

from functools import lru_cache

import pandas as pd

from backend.src.ai_agent.claims_agent import ClaimsAgent
from backend.src.ai_agent.ollama_client import OllamaClient
from backend.src.explainability.explain_score import explain_claim, risk_level
from backend.src.features.build_features import build_claim_contexts, build_model_features
from backend.src.ingestion.load_data import load_all_data
from backend.src.models.fraud_model import FraudRiskModel
from backend.src.services.database_service import save_agent_message, sync_risk_results, sync_source_tables


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


def list_claims() -> list[dict]:
    df = get_claims_dataset().sort_values("risk_score", ascending=False)
    columns = [
        "claim_id", "anonymous_customer", "line", "coverage", "city", "provider_name",
        "claim_amount", "risk_score", "risk_level", "risk_color", "recommended_action",
        "claim_date", "report_date",
    ]
    return [_clean_record(row) for row in df[columns].to_dict(orient="records")]


def get_claim(claim_id: str) -> dict | None:
    df = get_claims_dataset()
    match = df[df["claim_id"] == claim_id]
    if match.empty:
        return None
    return _clean_record(match.iloc[0].to_dict())


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
    response = ClaimsAgent(get_claims_dataset()).answer(message)
    save_agent_message("agente", response["answer"], response.get("provider", "reglas"), conversation_id)
    response["conversation_id"] = conversation_id
    return response


def agent_status() -> dict:
    return OllamaClient().status()


def sync_database() -> dict:
    source_counts = sync_source_tables()
    risk_counts = sync_risk_results(get_claims_dataset())
    return {"source": source_counts, "risk": risk_counts}
