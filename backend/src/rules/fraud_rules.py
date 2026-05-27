from __future__ import annotations

from datetime import datetime
from typing import Any

def _days_between(start: Any, end: Any) -> int:
    start_dt = datetime.fromisoformat(str(start))
    end_dt = datetime.fromisoformat(str(end))
    return int((end_dt - start_dt).days)


def _rule(code: str, name: str, points: int, explanation: str, severity: str) -> dict:
    return {
        "codigo": code,
        "nombre": name,
        "puntos": points,
        "explicacion": explanation,
        "severidad": severity,
    }


def evaluate_claim_rules(claim: dict, context: dict) -> list[dict]:
    rules: list[dict] = []
    policy = context.get("policy", {})
    provider = context.get("provider", {})
    documents = context.get("documents", {})
    customer_claim_count = int(context.get("customer_claim_count", 0))
    vehicle_claim_count = int(context.get("vehicle_claim_count", 0))
    provider_claim_count = int(context.get("provider_claim_count", 0))
    max_provider_claim_count = max(int(context.get("max_provider_claim_count", 1)), 1)
    similar_narrative_score = float(context.get("similar_narrative_score", 0))

    claim_date = claim.get("claim_date")
    report_date = claim.get("report_date")
    policy_start = policy.get("policy_start_date")
    policy_end = policy.get("policy_end_date")

    if claim_date and policy_start and _days_between(policy_start, claim_date) <= 30:
        rules.append(_rule(
            "POLICY_START_PROXIMITY",
            "Reclamo cercano al inicio de poliza",
            14,
            "El siniestro ocurrio dentro de los primeros 30 dias de vigencia; se recomienda validar antecedentes y documentacion.",
            "alta",
        ))

    if claim_date and policy_end and _days_between(claim_date, policy_end) <= 20:
        rules.append(_rule(
            "POLICY_END_PROXIMITY",
            "Reclamo cercano al fin de vigencia",
            10,
            "El evento se registro cerca del vencimiento de la poliza, lo que amerita revision adicional.",
            "media",
        ))

    if claim_date and report_date and _days_between(claim_date, report_date) > 7:
        rules.append(_rule(
            "LATE_REPORT",
            "Reporte tardio",
            9,
            "La fecha de reporte supera siete dias desde el evento declarado.",
            "media",
        ))

    if customer_claim_count >= 3:
        rules.append(_rule(
            "CUSTOMER_FREQUENCY",
            "Alta frecuencia de reclamos por asegurado",
            12,
            "El asegurado anonimo registra varios siniestros en el periodo sintetico analizado.",
            "alta",
        ))

    if vehicle_claim_count >= 3:
        rules.append(_rule(
            "VEHICLE_FREQUENCY",
            "Alta frecuencia de reclamos por vehiculo",
            11,
            "El vehiculo aparece asociado a multiples reclamos y requiere contraste documental.",
            "alta",
        ))

    if provider_claim_count >= max(6, int(max_provider_claim_count * 0.28)):
        rules.append(_rule(
            "RECURRENT_PROVIDER",
            "Proveedor recurrente",
            8,
            "El proveedor concentra una proporcion relevante de reclamos en la base sintetica.",
            "media",
        ))

    if bool(provider.get("restricted_simulated", False)):
        rules.append(_rule(
            "SIMULATED_RESTRICTED_PROVIDER",
            "Proveedor en lista restrictiva simulada",
            18,
            "El proveedor esta marcado en una lista restrictiva simulada para fines de demostracion.",
            "alta",
        ))

    if int(documents.get("missing_count", 0)) > 0:
        rules.append(_rule(
            "INCOMPLETE_DOCUMENTS",
            "Documentos incompletos",
            12,
            "Faltan documentos requeridos para completar la revision del siniestro.",
            "alta",
        ))

    if bool(documents.get("has_illegible", False)):
        rules.append(_rule(
            "ILLEGIBLE_DOCUMENTS",
            "Documentos ilegibles",
            9,
            "Uno o mas documentos fueron marcados como ilegibles y deben solicitarse nuevamente.",
            "media",
        ))

    if bool(documents.get("has_inconsistent", False)):
        rules.append(_rule(
            "INCONSISTENT_DOCUMENTS",
            "Documentos inconsistentes",
            15,
            "Existen diferencias entre documentos declarados y datos del siniestro.",
            "alta",
        ))

    claim_amount = float(claim.get("claim_amount", 0))
    insured_amount = max(float(policy.get("insured_amount", 1)), 1)
    if claim_amount / insured_amount >= 0.75:
        rules.append(_rule(
            "HIGH_AMOUNT_RATIO",
            "Monto reclamado alto frente a suma asegurada",
            13,
            "El monto reclamado representa una proporcion alta de la suma asegurada.",
            "alta",
        ))

    if similar_narrative_score >= 0.85:
        rules.append(_rule(
            "VERY_SIMILAR_NARRATIVE",
            "Narrativa muy similar a casos previos",
            13,
            "La descripcion textual tiene similitud superior al 85% con otro reclamo.",
            "alta",
        ))
    elif similar_narrative_score >= 0.70:
        rules.append(_rule(
            "SIMILAR_NARRATIVE",
            "Narrativa similar a casos previos",
            8,
            "La descripcion textual tiene similitud entre 70% y 84% con otro reclamo.",
            "media",
        ))

    coverage = str(claim.get("coverage", "")).lower()
    narrative = str(claim.get("narrative", "")).lower()

    if "perdida total" in coverage and "robo" in coverage:
        rules.append(_rule(
            "TOTAL_THEFT_COVERAGE",
            "Cobertura perdida total por robo",
            8,
            "La cobertura reclamada suele requerir validacion documental reforzada.",
            "media",
        ))

    if "sin tercero" in narrative or "no hubo testigos" in narrative:
        rules.append(_rule(
            "NO_THIRD_PARTY",
            "Accidente sin tercero identificado",
            7,
            "La narrativa no identifica tercero o testigos, por lo que conviene revisar soportes.",
            "media",
        ))

    suspicious_terms = ["zona aislada", "madrugada", "version cambia", "llaves dentro", "sin testigos"]
    if any(term in narrative for term in suspicious_terms):
        rules.append(_rule(
            "UNUSUAL_DYNAMICS",
            "Dinamica inusual declarada",
            10,
            "La narrativa contiene elementos que ameritan contraste con evidencias disponibles.",
            "media",
        ))

    if bool(claim.get("recent_customer_change", False)):
        rules.append(_rule(
            "RECENT_CUSTOMER_CHANGE",
            "Cambios recientes en datos del asegurado",
            8,
            "Se registraron cambios recientes en informacion del asegurado antes del reclamo.",
            "media",
        ))

    return rules


def score_rules(rules: list[dict]) -> int:
    return min(sum(int(rule["puntos"]) for rule in rules), 100)
