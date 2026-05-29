from __future__ import annotations

from difflib import get_close_matches
from datetime import datetime
from functools import lru_cache
import re

import pandas as pd

from backend.src.ai_agent.claims_agent import ClaimsAgent
from backend.src.ai_agent.ollama_client import OllamaClient
from backend.src.explainability.explain_score import explain_claim, risk_level
from backend.src.features.build_features import build_claim_contexts, build_model_features
from backend.src.models.fraud_model import FraudRiskModel
from backend.src.services.database_service import (
    get_latest_review_actions,
    has_source_data,
    load_source_tables,
    review_actions_summary,
    save_agent_message,
    source_table_counts,
    sync_risk_results,
)
from backend.src.services.hybrid_analysis_service import (
    has_claims_intent,
    hybrid_model_summary,
    predictive_preanalysis,
)
from backend.src.services.hackia_import_service import hackia_agent_context


@lru_cache(maxsize=1)
def get_claims_dataset() -> pd.DataFrame:
    if not has_source_data():
        return _empty_claims_dataset()

    data = load_source_tables()
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


def _empty_claims_dataset() -> pd.DataFrame:
    return pd.DataFrame({
        "claim_id": pd.Series(dtype="string"),
        "anonymous_customer": pd.Series(dtype="string"),
        "line": pd.Series(dtype="string"),
        "coverage": pd.Series(dtype="string"),
        "city": pd.Series(dtype="string"),
        "provider_name": pd.Series(dtype="string"),
        "claim_amount": pd.Series(dtype="float"),
        "risk_score": pd.Series(dtype="float"),
        "risk_level": pd.Series(dtype="string"),
        "risk_color": pd.Series(dtype="string"),
        "recommended_action": pd.Series(dtype="string"),
        "claim_date": pd.Series(dtype="string"),
        "report_date": pd.Series(dtype="string"),
        "provider_id": pd.Series(dtype="string"),
        "rules": pd.Series(dtype="object"),
        "missing_count": pd.Series(dtype="float"),
        "document_statuses": pd.Series(dtype="string"),
        "model_score": pd.Series(dtype="float"),
        "anomaly_score": pd.Series(dtype="float"),
        "nlp_score": pd.Series(dtype="float"),
        "rule_score": pd.Series(dtype="float"),
        "explainability": pd.Series(dtype="object"),
    })


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


def hybrid_status() -> dict:
    return hybrid_model_summary(get_claims_dataset())


def ask_agent(message: str, conversation_id: int | None = None) -> dict:
    conversation_id = save_agent_message("usuario", message, "usuario", conversation_id)
    corrected_message = _normalize_user_message(message)
    correction_response = _quality_gate_response(message, corrected_message)
    if correction_response:
        save_agent_message("agente", correction_response["answer"], correction_response["provider"], conversation_id)
        correction_response["conversation_id"] = conversation_id
        return correction_response

    quick_response = _light_ollama_response(corrected_message)
    if quick_response:
        save_agent_message("agente", quick_response["answer"], quick_response["provider"], conversation_id)
        quick_response["conversation_id"] = conversation_id
        return quick_response

    df = get_claims_dataset()
    if df.empty and has_claims_intent(corrected_message.lower()):
        hackia_context = _hackia_context_response(corrected_message) or hackia_agent_context(corrected_message)
        if hackia_context:
            response = {
                "answer": hackia_context,
                "related_claims": re.findall(r"SIN-\d{4,}", hackia_context.upper()),
                "provider": "mysql+pdf",
                "suggestions": ["Detalle de SIN-0003", "Top casos HackIA", "Documentos faltantes"],
                "disclaimer": "Lectura de apoyo para revision humana; no constituye una decision final.",
                "conversation_id": conversation_id,
            }
            save_agent_message("agente", response["answer"], response["provider"], conversation_id)
            return response

    response = ClaimsAgent(df, _review_context()).answer(corrected_message)
    hackia_context = _hackia_context_response(corrected_message)
    if hackia_context:
        response["answer"] = f"{response['answer']}\n\nContexto Excel/PDF HackIAthon:\n{hackia_context}"
        response["provider"] = "reglas+pdf"
    if corrected_message.strip().lower() != message.strip().lower():
        response["answer"] = f"Interpreté tu solicitud como: {corrected_message}.\n{response['answer']}"
    preanalysis = predictive_preanalysis(corrected_message, df, response.get("related_claims", []))
    if preanalysis:
        response["answer"] = f"{response['answer']}\n\nAnalisis predictivo previo:\n{preanalysis}"
    response = _rewrite_response_with_ollama(corrected_message, response)
    response = _format_claim_detail_response(corrected_message, response, df)
    save_agent_message("agente", response["answer"], response.get("provider", "reglas"), conversation_id)
    response["conversation_id"] = conversation_id
    return response


def _hackia_context_response(message: str) -> str | None:
    if not re.search(r"\b(SIN[- ]?\d{1,6}|pdf|ocr|factura|parte policial|declaraci[oó]n|excel|inconsistencia)\b", message, re.IGNORECASE):
        return None
    try:
        return hackia_agent_context(message) or None
    except Exception:
        return None


def _normalize_user_message(message: str) -> str:
    corrected_words = []
    terms = [
        "analisis", "caso", "casos", "ciudad", "ciudades", "documentos", "estado",
        "explica", "monto", "montos", "proveedor", "proveedores", "resumen", "riesgo",
        "score", "seguimiento", "siniestro", "siniestros", "top", "ultimos",
    ]
    aliases = {
        "analis": "analisis",
        "analisis": "analisis",
        "documetos": "documentos",
        "documento": "documentos",
        "prveedor": "proveedor",
        "provedor": "proveedor",
        "proveedro": "proveedor",
        "resuemn": "resumen",
        "rezumen": "resumen",
        "riesgos": "riesgo",
        "sinestro": "siniestro",
        "sinietro": "siniestro",
        "siniestros": "siniestros",
        "ultimos": "ultimos",
        "últimos": "ultimos",
    }
    for token in re.findall(r"CLM-\d{4,}|[A-Za-zÁÉÍÓÚáéíóúÑñ]+|\d+|[^\w\s]", message, flags=re.IGNORECASE):
        lower = token.lower()
        if re.fullmatch(r"clm-\d{4,}", lower):
            corrected_words.append(token.upper())
        elif lower in aliases:
            corrected_words.append(aliases[lower])
        elif lower.isalpha() and len(lower) >= 5:
            match = get_close_matches(lower, terms, n=1, cutoff=0.84)
            corrected_words.append(match[0] if match else token)
        else:
            corrected_words.append(token)
    return _join_tokens(corrected_words)


def _join_tokens(tokens: list[str]) -> str:
    text = " ".join(tokens)
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _quality_gate_response(original: str, corrected: str) -> dict | None:
    text = original.strip()
    normalized = corrected.lower()
    if not text:
        return _ask_for_clarification(original, "El mensaje llegó vacío.")
    if re.fullmatch(r"[^\wÁÉÍÓÚáéíóúÑñ]+", text):
        return _ask_for_clarification(original, "El mensaje no contiene una solicitud legible.")
    if len(re.sub(r"\W+", "", text)) <= 1:
        return _ask_for_clarification(original, "El mensaje es demasiado corto para interpretar una intención.")
    if _looks_like_noise(text) and not has_claims_intent(normalized):
        return _ask_for_clarification(original, "No logré detectar una intención clara.")
    return None


def _looks_like_noise(text: str) -> bool:
    words = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]{4,}", text.lower())
    if not words:
        return False
    vowel_words = sum(1 for word in words if re.search(r"[aeiouáéíóú]", word))
    repeated = bool(re.search(r"(.)\1{4,}", text.lower()))
    return repeated or (len(words) >= 2 and vowel_words / len(words) < 0.45)


def _ask_for_clarification(message: str, reason: str) -> dict:
    prompt = (
        "El usuario escribió una petición confusa para CheckIA. "
        "Pide aclaración de forma amable y breve. No inventes datos. "
        "Da 2 ejemplos concretos de preguntas válidas sobre siniestros. "
        f"Motivo detectado: {reason}\n"
        f"Mensaje del usuario: {message}"
    )
    fallback = "No logré entender la solicitud. Puedes preguntarme, por ejemplo: 'detalle de CLM-0129' o 'últimos 5 casos'."
    answer = _clean_light_answer(_strip_symbols(OllamaClient().generate(prompt, num_predict=80, timeout=12) or fallback))
    return {
        "answer": answer,
        "related_claims": [],
        "provider": "ollama correccion",
        "suggestions": ["Detalle de CLM-0129", "Últimos 5 casos", "Top 10 casos"],
        "disclaimer": "",
    }

def _rewrite_response_with_ollama(message: str, response: dict) -> dict:
    if response.get("provider") == "ollama":
        return response
    original_answer = response.get("answer", "")
    allowed_claims = set(response.get("related_claims") or [])
    allowed_text = ", ".join(sorted(allowed_claims)) if allowed_claims else "solo los IDs presentes en datos calculados"
    prompt = (
        "Redacta la respuesta final de CheckIA con tono natural, profesional y breve.\n"
        "Usa solo los datos calculados. No inventes IDs, montos, proveedores, ciudades ni metricas.\n"
        "No acuses fraude ni tomes decisiones finales.\n"
        "Conserva IDs CLM exactos y cifras importantes.\n\n"
        "Si hay una lista, mantenla compacta para que no se corte.\n"
        "Si hay analisis predictivo previo, integra score final, modelo, anomalia, NLP y factores explicables cuando sea relevante.\n"
        f"IDs permitidos: {allowed_text}.\n"
        f"Pregunta del usuario: {message}\n"
        f"Datos calculados:\n{original_answer}\n"
    )
    answer = OllamaClient().generate(prompt, num_predict=340, timeout=45)
    if not answer:
        response["answer"] = _strip_preanalysis_block(original_answer)
        return response
    cleaned = _clean_light_answer(_strip_symbols(answer))
    mentioned = set(re.findall(r"CLM-\d{4,}", cleaned))
    if allowed_claims and (mentioned - allowed_claims):
        cleaned = original_answer
    response["provider"] = "ollama + datos"
    response["answer"] = cleaned
    return response


def _format_claim_detail_response(message: str, response: dict, df: pd.DataFrame) -> dict:
    claim_ids = sorted(set(re.findall(r"CLM-\d{4,}", message.upper())))
    if len(claim_ids) != 1:
        return response
    claim_id = claim_ids[0]
    match = df[df["claim_id"] == claim_id]
    if match.empty:
        return response

    row = match.iloc[0]
    rules = row.get("rules", []) or []
    signal_lines = [f"- {rule['nombre']}" for rule in rules[:5]]
    if not signal_lines:
        signal_lines = ["- Sin reglas fuertes registradas"]

    action = row.get("recommended_action", "Revision humana recomendada")
    amount = float(row.get("claim_amount") or 0)
    response["provider"] = "ollama + datos"
    response["answer"] = (
        f"## {claim_id} - Riesgo {row.get('risk_level')} ({int(row.get('risk_score', 0))}/100)\n\n"
        f"**Resumen:** {action}. Esta lectura es apoyo para analisis humano, no una decision final.\n\n"
        "**Datos clave**\n"
        f"- Ciudad: {row.get('city')}\n"
        f"- Proveedor: {row.get('provider_name')}\n"
        f"- Monto: USD {amount:,.0f}\n"
        f"- Documentos: {row.get('document_statuses', 'sin detalle documental')}\n\n"
        "**Senales detectadas**\n"
        + "\n".join(signal_lines)
        + "\n\n"
        "**Lectura predictiva**\n"
        f"- Reglas: {float(row.get('rule_score', 0)):.1f}\n"
        f"- Modelo ML: {float(row.get('model_score', 0)):.1f}\n"
        f"- Anomalia: {float(row.get('anomaly_score', 0)):.1f}\n"
        f"- NLP: {float(row.get('nlp_score', 0)):.1f}\n\n"
        "**Siguiente paso**\n"
        "Validar documentos faltantes o inconsistentes, revisar la narrativa y contrastar el expediente antes de tomar acciones."
    )
    return response


def _strip_preanalysis_block(text: str) -> str:
    return text.split("\n\nAnalisis predictivo previo:", 1)[0].strip()


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
    if not has_claims_intent(normalized):
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

def _review_context() -> list[dict]:
    try:
        return review_actions_summary()
    except Exception:
        return []


def agent_status() -> dict:
    return OllamaClient().status()


def sync_database() -> dict:
    source_counts = source_table_counts()
    risk_counts = sync_risk_results(get_claims_dataset())
    return {"source": source_counts, "risk": risk_counts}
