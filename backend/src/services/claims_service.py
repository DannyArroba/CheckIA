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
    list_agent_messages,
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
from backend.src.services.hackia_import_service import hackia_agent_context, hackia_claim_detail, hackia_claims, hackia_executive_report, hackia_summary


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
        "bajo_observacion": "Bajo observaciÃ³n",
        "documentacion_solicitada": "DocumentaciÃ³n solicitada",
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
    memory = _recent_conversation_context(conversation_id)
    corrected_message = _normalize_user_message(message)
    correction_response = _quality_gate_response(message, corrected_message)
    if correction_response:
        save_agent_message("agente", correction_response["answer"], correction_response["provider"], conversation_id)
        correction_response["conversation_id"] = conversation_id
        return correction_response

    if _hackia_available() and _has_hackia_terms(corrected_message):
        response = _answer_with_hackia_ollama(corrected_message, memory)
        save_agent_message("agente", response["answer"], response["provider"], conversation_id)
        response["conversation_id"] = conversation_id
        return response

    quick_response = _light_ollama_response(corrected_message, memory)
    if quick_response:
        save_agent_message("agente", quick_response["answer"], quick_response["provider"], conversation_id)
        quick_response["conversation_id"] = conversation_id
        return quick_response

    if _hackia_available() and has_claims_intent(corrected_message.lower()):
        response = _answer_with_hackia_ollama(corrected_message, memory)
        save_agent_message("agente", response["answer"], response["provider"], conversation_id)
        response["conversation_id"] = conversation_id
        return response

    if not _hackia_available() and (has_claims_intent(corrected_message.lower()) or _has_hackia_terms(corrected_message)):
        response = {
            "answer": "**Respuesta**\n- Aun no hay dataset HackIAthon cargado. Sube el Excel y los PDFs desde Datos para que pueda responder con SIN, documentos y alertas reales.\n\n**Siguiente paso**\n- Carga el Excel nuevo y luego consulta por top casos, documentos faltantes o un SIN especifico.",
            "related_claims": [],
            "provider": "sistema",
            "suggestions": ["Subir Excel en Datos", "Top 10 casos", "Documentos faltantes"],
            "disclaimer": "",
            "conversation_id": conversation_id,
        }
        save_agent_message("agente", response["answer"], response["provider"], conversation_id)
        return response

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
        response["answer"] = f"InterpretÃ© tu solicitud como: {corrected_message}.\n{response['answer']}"
    preanalysis = predictive_preanalysis(corrected_message, df, response.get("related_claims", []))
    if preanalysis:
        response["answer"] = f"{response['answer']}\n\nAnalisis predictivo previo:\n{preanalysis}"
    response = _rewrite_response_with_ollama(corrected_message, response, memory)
    response = _format_claim_detail_response(corrected_message, response, df)
    save_agent_message("agente", response["answer"], response.get("provider", "reglas"), conversation_id)
    response["conversation_id"] = conversation_id
    return response


def _hackia_context_response(message: str) -> str | None:
    if not re.search(r"\b(SIN[- ]?\d{1,6}|pdf|ocr|factura|parte policial|declaraci[oÃ³]n|excel|inconsistencia)\b", message, re.IGNORECASE):
        return None
    try:
        return hackia_agent_context(message) or None
    except Exception:
        return None


def _hackia_available() -> bool:
    try:
        return int(hackia_summary().get("counts", {}).get("siniestros", 0) or 0) > 0
    except Exception:
        return False


def _plain(value: str) -> str:
    normalized = value.lower()
    normalized = normalized.replace("Ã¡", "a").replace("Ã©", "e").replace("Ã­", "i").replace("Ã³", "o").replace("Ãº", "u").replace("Ã±", "n")
    return normalized


def _has_hackia_terms(message: str) -> bool:
    normalized = _plain(message)
    return bool(re.search(r"\b(sin-\d{4,6}|siniestro|siniestros|caso|casos|factura|facturas|pdf|ocr|parte|policial|declaracion|documento|documentos|proveedor|proveedores|ciudad|ciudades|riesgo|alerta|alertas|score|poliza|asegurado|excel|inconsistencia|inconsistencias|prioridad|prioriza|priorizar|priorizado|top|resumen|ejecutivo)\b", normalized))


def _recent_conversation_context(conversation_id: int | None) -> str:
    if not conversation_id:
        return ""
    try:
        rows = list_agent_messages(conversation_id)[-8:]
    except Exception:
        return ""
    compact = []
    for row in rows:
        text = re.sub(r"\s+", " ", str(row.get("message_text") or "")).strip()
        if text:
            compact.append(f"{row.get('role')}: {text[:260]}")
    return "\n".join(compact)


def _answer_with_hackia_ollama(message: str, memory: str) -> dict:
    data_context, fallback_answer, related = _hackia_brief(message)
    prompt = (
        "Eres el agente CheckIA para revision de siniestros de seguros.\n"
        "Responde SIEMPRE en espanol claro, amable, conciso y util.\n"
        "Usa solo el contexto limpio entregado. No copies el contexto literalmente y no muestres diccionarios, JSON, objetos Python ni texto PDF completo.\n"
        "No inventes datos que no aparezcan en el contexto.\n"
        "No acuses fraude, no niegues siniestros y no tomes decisiones legales.\n"
        "Si la pregunta es corta, responde corto. Si pide detalle, usa maximo 6 vinetas.\n"
        "Formato obligatorio:\n"
        "**Respuesta**\n"
        "- respuesta directa a la pregunta\n"
        "**Evidencia usada**\n"
        "- fuente y dato relevante\n"
        "**Siguiente paso**\n"
        "- accion de revision humana\n"
        "Si el usuario saluda o pregunta algo casual, responde natural y breve, sin analizar datos.\n\n"
        f"Memoria reciente de la conversacion:\n{memory or 'Sin historial relevante.'}\n\n"
        f"Pregunta del usuario:\n{message}\n\n"
        f"Contexto limpio disponible:\n{data_context}\n"
    )
    answer = OllamaClient().generate(prompt, num_predict=220, timeout=22)
    if not answer:
        answer = fallback_answer
    cleaned = _clean_structured_answer(_strip_symbols(answer))
    if _answer_leaked_context(cleaned):
        cleaned = fallback_answer
    return {
        "answer": cleaned,
        "related_claims": related or sorted(set(re.findall(r"SIN-\d{4,6}", f"{cleaned} {data_context}".upper()))),
        "provider": "ollama + excel/pdf",
        "suggestions": _predictive_suggestions(message, cleaned),
        "disclaimer": "Lectura de apoyo para revision humana; no constituye acusacion ni decision final.",
    }


def _hackia_brief(message: str) -> tuple[str, str, list[str]]:
    ids = sorted(set(re.findall(r"SIN\s*[- ]?\s*\d{1,6}", message.upper())))
    normalized = _plain(message)
    if ids:
        sid = re.sub(r"SIN\s*[- ]?\s*(\d{1,6})", lambda m: f"SIN-{int(m.group(1)):04d}", ids[0])
        detail = hackia_claim_detail(sid)
        if not detail:
            fallback = f"**Respuesta**\n- No encontre el siniestro {sid} en el dataset cargado.\n\n**Siguiente paso**\n- Verifica el ID o vuelve a importar el Excel."
            return fallback, fallback, [sid]
        return _brief_for_claim(detail, normalized)
    if "resumen" in normalized or "ejecutivo" in normalized:
        return _brief_for_summary()
    top = hackia_claims()[:10]
    lines = [f"{row.get('id_siniestro')}: score {row.get('puntaje_riesgo')} ({row.get('nivel_riesgo')}), ciudad {row.get('ciudad')}, alertas {row.get('alertas')}" for row in top]
    context = "Top casos priorizados:\n" + "\n".join(f"- {line}" for line in lines)
    fallback = "**Respuesta**\n" + "\n".join(f"- {line}" for line in lines[:5]) + "\n\n**Evidencia usada**\n- Ranking por score y alertas calculadas.\n\n**Siguiente paso**\n- Revisar primero los casos con mayor score y documentos pendientes."
    return context, fallback, [row.get("id_siniestro") for row in top if row.get("id_siniestro")]


def _brief_for_claim(detail: dict, normalized: str) -> tuple[str, str, list[str]]:
    siniestro = detail.get("siniestro") or {}
    analisis = detail.get("analisis") or {}
    proveedor = detail.get("proveedor") or {}
    documentos = detail.get("documentos") or []
    alertas = detail.get("alertas") or []
    facturas = detail.get("facturas") or []
    partes = detail.get("partes_policiales") or []
    declaraciones = detail.get("declaraciones") or []
    sid = siniestro.get("id_siniestro", "SIN")

    doc_lines = [
        _fix_chat_text(f"{doc.get('id_documento')}: {doc.get('tipo_documento') or 'Documento'} | PDF {'encontrado' if not doc.get('pdf_no_encontrado') else 'faltante'} | archivo {doc.get('nombre_archivo_pdf') or 'sin nombre'}")
        for doc in documentos[:10]
    ]
    alert_lines = [_friendly_alert_line(alert) for alert in alertas[:8]]
    invoice_lines = [
        f"Factura {fact.get('numero_factura') or '-'}: total {fact.get('total_pagar') or '-'}, RUC {fact.get('ruc') or '-'}, caso PDF {fact.get('caso_marcado') or '-'}, alterado={bool(fact.get('documento_alterado'))}"
        for fact in facturas[:4]
    ]
    police_lines = [
        f"Parte {part.get('numero_parte_policial') or '-'}: placa {part.get('placa') or '-'}, fecha {part.get('fecha') or '-'}, tipo {part.get('tipo_accidente') or '-'}"
        for part in partes[:3]
    ]
    declaration_lines = [
        f"Declaracion: asegurado {dec.get('asegurado') or '-'}, placa {dec.get('placa') or '-'}, fecha {dec.get('fecha_accidente') or '-'}"
        for dec in declaraciones[:3]
    ]

    context = (
        f"Caso {sid}\n"
        f"Score: {analisis.get('puntaje_riesgo', 0)}/100 ({analisis.get('nivel_riesgo', 'Bajo')})\n"
        f"Ramo/cobertura: {siniestro.get('ramo') or '-'} / {siniestro.get('cobertura') or '-'}\n"
        f"Ciudad: {siniestro.get('ciudad') or siniestro.get('sucursal') or '-'}\n"
        f"Proveedor: {proveedor.get('nombre_proveedor') or siniestro.get('id_proveedor') or '-'}\n"
        f"Monto reclamado: {siniestro.get('monto_reclamado') or '-'}\n"
        f"Explicacion score: {analisis.get('explicacion') or '-'}\n"
        "Documentos:\n- " + ("\n- ".join(doc_lines) if doc_lines else "Sin documentos registrados") + "\n"
        "Alertas:\n- " + ("\n- ".join(alert_lines) if alert_lines else "Sin alertas registradas") + "\n"
        "Facturas:\n- " + ("\n- ".join(invoice_lines) if invoice_lines else "Sin facturas procesadas") + "\n"
        "Partes policiales:\n- " + ("\n- ".join(police_lines) if police_lines else "Sin parte policial procesado") + "\n"
        "Declaraciones:\n- " + ("\n- ".join(declaration_lines) if declaration_lines else "Sin declaracion procesada")
    )

    if "document" in normalized or "pdf" in normalized:
        answer = f"**Respuesta**\n" + "\n".join(f"- {line}" for line in doc_lines[:8]) + "\n\n**Evidencia usada**\n- Hoja Documentos del Excel y PDFs vinculados/procesados.\n\n**Siguiente paso**\n- Subir o validar los PDFs marcados como faltantes antes de cerrar la revision."
    elif "prioriza" in normalized or "prioridad" in normalized or "priorizar" in normalized or "por que" in normalized:
        answer = f"**Respuesta**\n- {sid} se prioriza por score {analisis.get('puntaje_riesgo', 0)}/100 ({analisis.get('nivel_riesgo', 'Bajo')}).\n" + "\n".join(f"- {line}" for line in alert_lines[:5]) + "\n\n**Evidencia usada**\n- Excel, alertas calculadas y PDFs procesados.\n\n**Siguiente paso**\n- Validar evidencias documentales y contrastar fechas, proveedor y factura antes de cualquier decision."
    elif "inconsistencia" in normalized:
        inconsistent = [line for line in alert_lines if any(word in line.lower() for word in ["inconsistente", "faltante", "invalido", "invÃ¡lido", "expirada", "superior"])]
        answer = f"**Respuesta**\n" + "\n".join(f"- {line}" for line in (inconsistent[:6] or alert_lines[:6])) + "\n\n**Evidencia usada**\n- Alertas de Excel/PDF/OCR.\n\n**Siguiente paso**\n- Revisar los campos marcados y corregir o confirmar la evidencia de soporte."
    else:
        answer = f"**Respuesta**\n- {sid}: score {analisis.get('puntaje_riesgo', 0)}/100 ({analisis.get('nivel_riesgo', 'Bajo')}), {len(alertas)} alertas y {len(documentos)} documentos registrados.\n- Proveedor: {proveedor.get('nombre_proveedor') or siniestro.get('id_proveedor') or '-'}.\n\n**Evidencia usada**\n- Excel, documentos vinculados y analisis de alertas.\n\n**Siguiente paso**\n- Abrir el detalle del caso y revisar las alertas principales."
    return context, answer, [sid]


def _brief_for_summary() -> tuple[str, str, list[str]]:
    report = hackia_executive_report()
    summary = hackia_summary()
    counts = summary.get("counts", {})
    risk = summary.get("risk_distribution", [])
    providers = report.get("providers", [])[:5]
    cities = report.get("cities", [])[:5]
    top = hackia_claims()[:5]
    risk_text = ", ".join(f"{item.get('nivel_riesgo')}: {item.get('total')}" for item in risk)
    context = (
        f"Resumen ejecutivo: siniestros={counts.get('siniestros', 0)}, documentos={counts.get('documentos', 0)}, alertas={counts.get('alertas_fraude', 0)}\n"
        f"Distribucion: {risk_text}\n"
        "Proveedores destacados:\n- " + "\n- ".join(f"{p.get('provider_name')} ({p.get('alerts')} alertas, score prom. {p.get('avg_score')})" for p in providers) + "\n"
        "Ciudades destacadas:\n- " + "\n- ".join(f"{c.get('city')} ({c.get('claims')} casos)" for c in cities) + "\n"
        "Top casos:\n- " + "\n- ".join(f"{c.get('id_siniestro')} score {c.get('puntaje_riesgo')} {c.get('nivel_riesgo')}" for c in top)
    )
    fallback = (
        f"**Respuesta**\n- Dataset activo: {counts.get('siniestros', 0)} siniestros, {counts.get('documentos', 0)} documentos y {counts.get('alertas_fraude', 0)} alertas de revision.\n"
        f"- Distribucion de riesgo: {risk_text or 'sin datos'}.\n"
        f"- Casos prioritarios: {', '.join(c.get('id_siniestro') for c in top if c.get('id_siniestro'))}.\n\n"
        "**Evidencia usada**\n- Excel importado, PDFs procesados, alertas y scoring.\n\n"
        "**Siguiente paso**\n- Revisar primero los casos con score alto/critico y documentos faltantes."
    )
    return context, fallback, [c.get("id_siniestro") for c in top if c.get("id_siniestro")]


def _answer_leaked_context(answer: str) -> bool:
    lowered = answer.lower()
    return any(marker in lowered for marker in ["contexto hackiathon", "analisis={", "datetime.datetime", "texto_pdf=", "documento sintetico", "ministerio del interior"]) or len(answer) > 2500


def _friendly_alert_line(alert: dict) -> str:
    field = str(alert.get("campo_detectado") or "").lower()
    severity = str(alert.get("severidad") or "media")
    source = _ascii_chat_text(_fix_chat_text(str(alert.get("fuente_evidencia") or "datos")))
    found = _ascii_chat_text(_fix_chat_text(str(alert.get("valor_encontrado") or "")))
    if field == "fecha_siniestro":
        return f"Poliza expirada al momento del siniestro ({severity}, fuente {source}): la fecha del evento queda fuera de la vigencia esperada."
    if field == "id_proveedor":
        return f"Proveedor en lista restrictiva ({severity}, fuente {source}): el proveedor requiere revision especial."
    if field == "siniestros_asociados":
        return f"Proveedor con alta concentracion de siniestros ({severity}, fuente {source}): registra {found or 'varios'} casos asociados."
    if field == "ruc":
        return f"Factura con RUC invalido ({severity}, fuente {source}): el RUC extraido no cumple la validacion basica."
    if field == "total_pagar":
        return f"Factura superior al promedio del proveedor ({severity}, fuente {source}): el total facturado supera el umbral esperado."
    if field == "dias_ocurrencia_reporte":
        return f"Dias de reporte inconsistente ({severity}, fuente {source}): la columna operativa no coincide con la diferencia entre fechas."
    if field == "documentos_pdf":
        return f"PDFs faltantes ({severity}, fuente {source}): hay documentos del Excel sin archivo PDF vinculado."
    if field == "docs_completos":
        return f"Documentacion incompleta ({severity}, fuente {source}): el expediente figura como incompleto."
    label = _ascii_chat_text(_fix_chat_text(str(alert.get("tipo_alerta") or "Alerta de revision")))
    explanation = _ascii_chat_text(_fix_chat_text(str(alert.get("explicacion") or "Requiere revision humana.")))
    return f"{label} ({severity}, fuente {source}): {explanation}"


def _fix_chat_text(value: str) -> str:
    text = str(value)
    for _ in range(3):
        if not any(marker in text for marker in ["Ã", "Â", "â"]):
            break
        try:
            text = text.encode("latin1").decode("utf-8")
        except UnicodeError:
            break
    return text


def _ascii_chat_text(value: str) -> str:
    text = str(value)
    replacements = {
        "ÃÂ¡": "a", "ÃÂ©": "e", "ÃÂ­": "i", "ÃÂ³": "o", "ÃÂº": "u", "ÃÂ±": "n",
        "Ã¡": "a", "Ã©": "e", "Ã­": "i", "Ã³": "o", "Ãº": "u", "Ã±": "n",
        "Ã": "A", "Ã‰": "E", "Ã": "I", "Ã“": "O", "Ãš": "U", "Ã‘": "N",
        "Â": "",
        "�": "",
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def _normalize_user_message(message: str) -> str:
    aliases = {
        "aÃ±alisis": "analisis", "analise": "analisis", "analiza": "analiza", "analisar": "analizar",
        "analis": "analisis", "analizis": "analisis", "comporbando": "comprobando",
        "documetos": "documentos", "docuentos": "documentos", "docs": "documentos",
        "exxcel": "excel", "exel": "excel", "ecxel": "excel",
        "fraudes": "posibles riesgos", "fraude": "posible riesgo",
        "polizas": "polizas", "poliza": "poliza", "polizaas": "polizas",
        "prveedor": "proveedor", "provedor": "proveedor", "proveedro": "proveedor",
        "resuemn": "resumen", "rezumen": "resumen",
        "riesgos": "riesgo", "riesgoz": "riesgo",
        "sinestro": "siniestro", "sinietro": "siniestro", "sisniestro": "siniestro", "sisniestros": "siniestros",
        "sinietro": "siniestro", "sinietros": "siniestros", "siniestro": "siniestro",
        "factra": "factura", "factrua": "factura",
        "declaracion": "declaracion", "declarasion": "declaracion",
        "inconsitencia": "inconsistencia", "inconsistensia": "inconsistencia",
        "priorisar": "priorizar", "prioriza": "prioriza",
        "q": "que", "k": "que",
    }
    terms = [
        "analisis", "analizar", "alertas", "asegurado", "caso", "casos", "ciudad", "ciudades",
        "declaracion", "documentos", "excel", "factura", "inconsistencia", "monto", "montos",
        "ocr", "parte", "pdf", "poliza", "proveedor", "proveedores", "resumen", "riesgo",
        "score", "seguimiento", "siniestro", "siniestros", "top", "ultimos",
    ]
    tokens = re.findall(r"SIN[-\s]?\d{1,6}|CLM-\d{4,}|[A-Za-zÃÃ‰ÃÃ“ÃšÃ¡Ã©Ã­Ã³ÃºÃ‘Ã±]+|\d+|[^\w\s]", message, flags=re.IGNORECASE)
    corrected = []
    for token in tokens:
        raw = token.lower()
        plain = _plain(raw)
        if re.fullmatch(r"sin[-\s]?\d{1,6}", raw, flags=re.IGNORECASE):
            corrected.append(re.sub(r"SIN[-\s]?(\d{1,6})", lambda m: f"SIN-{int(m.group(1)):04d}", token.upper()))
        elif re.fullmatch(r"clm-\d{4,}", raw):
            corrected.append(token.upper())
        elif plain in aliases:
            corrected.append(aliases[plain])
        elif plain.isalpha() and len(plain) >= 5:
            match = get_close_matches(plain, terms, n=1, cutoff=0.76)
            corrected.append(match[0] if match else token)
        else:
            corrected.append(token)
    return _join_tokens(corrected)

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
        "Ãºltimos": "ultimos",
    }
    for token in re.findall(r"CLM-\d{4,}|[A-Za-zÃÃ‰ÃÃ“ÃšÃ¡Ã©Ã­Ã³ÃºÃ‘Ã±]+|\d+|[^\w\s]", message, flags=re.IGNORECASE):
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
        return _ask_for_clarification(original, "El mensaje llegÃ³ vacÃ­o.")
    if re.fullmatch(r"[^\wÃÃ‰ÃÃ“ÃšÃ¡Ã©Ã­Ã³ÃºÃ‘Ã±]+", text):
        return _ask_for_clarification(original, "El mensaje no contiene una solicitud legible.")
    if len(re.sub(r"\W+", "", text)) <= 1:
        return _ask_for_clarification(original, "El mensaje es demasiado corto para interpretar una intenciÃ³n.")
    if _looks_like_noise(text) and not has_claims_intent(normalized):
        return _ask_for_clarification(original, "No logrÃ© detectar una intenciÃ³n clara.")
    return None


def _looks_like_noise(text: str) -> bool:
    words = re.findall(r"[A-Za-zÃÃ‰ÃÃ“ÃšÃ¡Ã©Ã­Ã³ÃºÃ‘Ã±]{4,}", text.lower())
    if not words:
        return False
    vowel_words = sum(1 for word in words if re.search(r"[aeiouÃ¡Ã©Ã­Ã³Ãº]", word))
    repeated = bool(re.search(r"(.)\1{4,}", text.lower()))
    return repeated or (len(words) >= 2 and vowel_words / len(words) < 0.45)


def _ask_for_clarification(message: str, reason: str) -> dict:
    prompt = (
        "El usuario escribiÃ³ una peticiÃ³n confusa para CheckIA. "
        "Pide aclaraciÃ³n de forma amable y breve. No inventes datos. "
        "Da 2 ejemplos concretos de preguntas vÃ¡lidas sobre siniestros. "
        f"Motivo detectado: {reason}\n"
        f"Mensaje del usuario: {message}"
    )
    fallback = "No logre entender la solicitud. Puedes preguntarme, por ejemplo: 'Que documentos tiene SIN-0022' o 'Resumen ejecutivo'."
    answer = _clean_light_answer(_strip_symbols(OllamaClient().generate(prompt, num_predict=80, timeout=12) or fallback))
    return {
        "answer": answer,
        "related_claims": [],
        "provider": "ollama correccion",
        "suggestions": ["Que documentos tiene SIN-0022", "Resumen ejecutivo", "Top 10 casos"],
        "disclaimer": "",
    }

def _rewrite_response_with_ollama(message: str, response: dict, memory: str = "") -> dict:
    if response.get("provider") == "ollama":
        return response
    original_answer = response.get("answer", "")
    allowed_claims = set(response.get("related_claims") or [])
    allowed_text = ", ".join(sorted(allowed_claims)) if allowed_claims else "solo los IDs presentes en datos calculados"
    prompt = (
        "Redacta la respuesta final de CheckIA con tono natural, profesional y breve.\n"
        "Usa solo los datos calculados. No inventes IDs, montos, proveedores, ciudades ni metricas.\n"
        "No acuses fraude ni tomes decisiones finales.\n"
        "Conserva IDs SIN o CLM exactos y cifras importantes.\n\n"
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
    mentioned = set(re.findall(r"(?:SIN-\d{4,6}|CLM-\d{4,})", cleaned))
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


def _light_ollama_response(message: str, memory: str = "") -> dict | None:
    text = message.strip().lower()
    normalized = re.sub(r"[Â¿?Â¡!.,;:]+", "", text)
    simple_greetings = {
        "hola", "holi", "holis", "buenas", "hey", "holaa", "hello", "hi", "buenos dias", "buenos dÃ­as",
        "buenas tardes", "buenas noches", "que tal", "quÃ© tal"
    }
    wellbeing = {
        "como estas", "cÃ³mo estÃ¡s", "como esta", "cÃ³mo estÃ¡", "como vas", "cÃ³mo vas",
        "que haces", "quÃ© haces", "todo bien", "como te va", "cÃ³mo te va"
    }
    thanks = {"gracias", "ok", "listo", "vale", "perfecto", "dale", "entendido", "ya"}

    if normalized in simple_greetings:
        return _ask_ollama_light(
            message, memory,
            fallback="Hola. Que quieres revisar: casos criticos, proveedores, documentos o seguimientos?",
            suggestions=["Top 10 casos", "Proveedores con alertas", "Resumen ejecutivo"],
        )
    if normalized in wellbeing:
        return _ask_ollama_light(
            message, memory,
            fallback="Estoy bien, listo para ayudarte con CheckIA. Si quieres, revisamos casos criticos o un resumen rapido.",
            suggestions=["Top 10 casos", "Resumen ejecutivo"],
        )
    if normalized in thanks:
        return _ask_ollama_light(
            message, memory,
            fallback="Listo. Cuando quieras, seguimos revisando siniestros.",
            suggestions=["Top 10 casos", "Seguimiento humano"],
        )
    if normalized in {"que puedes hacer", "quÃ© puedes hacer", "ayuda", "help", "ayudame", "ayÃºdame"}:
        return _ask_ollama_light(
            message, memory,
            fallback="Puedo resumir riesgos, listar casos prioritarios, revisar proveedores, documentos, ciudades y seguimientos humanos.",
            suggestions=["Top 10 casos", "Documentos crÃ­ticos", "Seguimiento humano"],
        )
    if not has_claims_intent(normalized):
        return _ask_ollama_light(
            message, memory,
            fallback="Si, puedo ayudarte con eso. Si quieres, tambien puedo revisar informacion de siniestros.",
            suggestions=["Top 10 casos", "Resumen ejecutivo"],
        )
    return None


def _ask_ollama_light(message: str, memory: str, fallback: str, suggestions: list[str]) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = (
        "El usuario hizo una interacciÃ³n simple dentro de CheckIA. "
        "Responde con tono amable, natural y muy breve. "
        "No analices datos de siniestros, no menciones casos especÃ­ficos y no inventes cifras. "
        f"Fecha actual del sistema: {today}. Si pregunta por la fecha o el dÃ­a, responde usando esa fecha. "
        "No uses emojis. MÃ¡ximo 25 palabras.\n\n"
        f"Mensaje del usuario: {message}"
    )
    raw_answer = OllamaClient().generate(prompt, num_predict=45, timeout=10)
    answer = _clean_light_answer(_strip_symbols(raw_answer or fallback))
    if _answer_has_encoding_noise(answer):
        answer = fallback
    return {
        "answer": answer,
        "related_claims": [],
        "provider": "ollama ligero",
        "suggestions": suggestions,
        "disclaimer": "",
    }


def _strip_symbols(text: str) -> str:
    return re.sub(r"[\U00010000-\U0010ffff]", "", text).strip()


def _answer_has_encoding_noise(text: str) -> bool:
    return any(marker in text for marker in ["Ã", "Â", "�", "??"])


def _clean_light_answer(text: str) -> str:
    text = _ascii_chat_text(_fix_chat_text(text))
    blocked = [
        "CheckIA no puede tomar decisiones",
        "no puede tomar decisiones legales",
        "Recuerda que CheckIA",
        "Requiere anÃ¡lisis humano",
    ]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    kept = [line for line in lines if not any(phrase.lower() in line.lower() for phrase in blocked)]
    return " ".join(kept).strip() or text.strip()


def _clean_structured_answer(text: str) -> str:
    cleaned = _ascii_chat_text(_fix_chat_text(_strip_symbols(text))).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = re.sub(r"(?<!\n)(\*\*(?:Respuesta|Evidencia usada|Siguiente paso|Datos clave|Alertas|Resumen):?\*\*)", r"\n\n\1\n", cleaned)
    cleaned = re.sub(r"\s+-\s+", "\n- ", cleaned)
    cleaned = cleaned.replace("fraude confirmado", "posible riesgo").replace("Fraude confirmado", "Posible riesgo")
    return cleaned.strip() or "No encontre suficiente contexto para responder con datos cargados."


def _predictive_suggestions(message: str, answer: str) -> list[str]:
    ids = sorted(set(re.findall(r"SIN-\d{4,6}", f"{message} {answer}".upper())))
    if ids:
        return [f"Que documentos tiene {ids[0]}", f"Por que se prioriza {ids[0]}", f"Ver inconsistencias de {ids[0]}"]
    normalized = _plain(message)
    if "proveedor" in normalized:
        return ["Top casos del proveedor", "Proveedores con mas alertas", "Resumen ejecutivo"]
    if "document" in normalized or "pdf" in normalized:
        return ["Documentos faltantes", "Facturas alteradas", "Campos extraidos por OCR"]
    return ["Top 10 casos", "Documentos faltantes", "Resumen ejecutivo"]


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
