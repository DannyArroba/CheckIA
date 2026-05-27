def risk_level(score: float) -> dict:
    if score <= 40:
        return {"nivel": "Bajo", "color": "Verde", "accion": "Revision estandar"}
    if score <= 75:
        return {"nivel": "Medio", "color": "Amarillo", "accion": "Revision recomendada"}
    return {"nivel": "Alto", "color": "Rojo", "accion": "Caso prioritario para analisis humano"}


def explain_claim(row: dict) -> dict:
    rules = row.get("rules", [])
    top_rules = sorted(rules, key=lambda rule: rule["puntos"], reverse=True)[:4]
    level = risk_level(float(row.get("risk_score", 0)))
    factors = [rule["nombre"] for rule in top_rules]
    if not factors:
        factors = ["No se activaron senales relevantes en las reglas de negocio."]

    explanation = (
        f"El caso presenta un nivel {level['nivel'].lower()} de posible riesgo. "
        f"El score combina reglas explicables, analisis de anomalias y similitud textual. "
        f"La recomendacion es: {level['accion'].lower()}."
    )

    return {
        "explicacion": explanation,
        "factores": factors,
        "recomendacion": level["accion"],
        "mensaje_etico": "Esta alerta no constituye una acusacion de fraude. El caso requiere revision humana antes de cualquier decision.",
    }
