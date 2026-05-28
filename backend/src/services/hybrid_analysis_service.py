from __future__ import annotations

import re

import pandas as pd


def hybrid_model_summary(df: pd.DataFrame) -> dict:
    high = int((df["risk_level"] == "Alto").sum())
    medium = int((df["risk_level"] == "Medio").sum())
    low = int((df["risk_level"] == "Bajo").sum())
    top = df.nlargest(5, "risk_score")
    rule_counts: dict[str, int] = {}
    for active_rules in df["rules"]:
        for rule in active_rules:
            rule_counts[rule["nombre"]] = rule_counts.get(rule["nombre"], 0) + 1

    return {
        "approach": "Enfoque híbrido: ML + NLP + agente de IA para consultas en lenguaje natural.",
        "layers": [
            {"name": "Reglas explicables", "weight": 0.70, "implemented": True},
            {"name": "ML/anomalías", "weight": 0.20, "implemented": True},
            {"name": "NLP/similitud textual", "weight": 0.10, "implemented": True},
            {"name": "Agente IA/Ollama", "weight": None, "implemented": True},
        ],
        "total_cases": int(len(df)),
        "risk_distribution": {"alto": high, "medio": medium, "bajo": low},
        "main_signals": [
            {"signal": name, "count": count}
            for name, count in sorted(rule_counts.items(), key=lambda item: item[1], reverse=True)[:5]
        ],
        "top_cases": [
            {
                "claim_id": row.claim_id,
                "risk_score": int(row.risk_score),
                "risk_level": row.risk_level,
                "model_score": float(row.model_score),
                "anomaly_score": float(row.anomaly_score),
                "nlp_score": float(row.nlp_score),
            }
            for row in top.itertuples()
        ],
    }


def predictive_preanalysis(message: str, df: pd.DataFrame, related_claims: list[str]) -> str:
    normalized = message.lower()
    claim_ids = sorted(set(re.findall(r"CLM-\d{4,}", message.upper()) + related_claims))
    if claim_ids:
        compact = len(claim_ids) > 3 and not re.search(r"\b(explica|detalle|detalla|por que|por qué)\b", normalized)
        return _claim_preanalysis(df[df["claim_id"].isin(claim_ids)].head(10), compact=compact)

    if not has_claims_intent(normalized):
        return ""

    summary = hybrid_model_summary(df)
    top_text = "; ".join(
        f"{item['claim_id']} score {item['risk_score']} modelo {item['model_score']:.1f} anomalia {item['anomaly_score']:.1f}"
        for item in summary["top_cases"][:3]
    )
    signals = ", ".join(f"{item['signal']} ({item['count']})" for item in summary["main_signals"][:3])
    return (
        f"Dataset {summary['total_cases']} casos: {summary['risk_distribution']['alto']} altos, "
        f"{summary['risk_distribution']['medio']} medios. Señales dominantes: {signals or 'sin señales dominantes'}. "
        f"Casos modelo prioritarios: {top_text}."
    )


def has_claims_intent(text: str) -> bool:
    terms = [
        "caso", "casos", "siniestro", "siniestros", "riesgo", "riesgos", "fraude",
        "proveedor", "proveedores", "documento", "documentos", "monto", "montos",
        "ciudad", "ciudades", "seguimiento", "observacion", "observación", "estado",
        "poliza", "póliza", "reporte", "score", "alerta", "alertas", "resumen",
        "dashboard", "rojo", "amarillo", "verde", "top", "revisar", "revisión",
        "revision", "asegurado", "aseguradora", "cobertura", "claim", "clm-",
    ]
    return any(term in text for term in terms)


def _claim_preanalysis(subset: pd.DataFrame, compact: bool = False) -> str:
    lines = []
    for row in subset.itertuples():
        if compact:
            lines.append(
                f"{row.claim_id}: final {int(row.risk_score)} {row.risk_level}; "
                f"modelo {float(row.model_score):.1f}; anomalia {float(row.anomaly_score):.1f}; nlp {float(row.nlp_score):.1f}"
            )
            continue
        explanation = row.explainability if isinstance(row.explainability, dict) else {}
        factors = explanation.get("factores", [])
        factor_text = ", ".join(factors[:4]) if factors else "sin factores explicables registrados"
        lines.append(
            f"{row.claim_id}: score final {int(row.risk_score)} {row.risk_level}; "
            f"reglas {float(row.rule_score):.1f}; modelo {float(row.model_score):.1f}; "
            f"anomalia {float(row.anomaly_score):.1f}; nlp {float(row.nlp_score):.1f}; "
            f"factores: {factor_text}; recomendacion: {row.recommended_action}"
        )
    return " ".join(lines)
