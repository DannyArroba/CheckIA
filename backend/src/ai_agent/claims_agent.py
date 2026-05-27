from __future__ import annotations

import pandas as pd


class ClaimsAgent:
    def __init__(self, claims: pd.DataFrame) -> None:
        self.claims = claims

    def answer(self, question: str) -> dict:
        q = question.lower().strip()
        if not q:
            return self._response("Escribe una pregunta sobre los siniestros cargados para ayudarte con datos del sistema.")

        if "10" in q and "mayor riesgo" in q:
            top = self.claims.nlargest(10, "risk_score")
            lines = [f"{r.claim_id}: score {int(r.risk_score)} ({r.risk_level}) - {r.city}, {r.provider_name}" for r in top.itertuples()]
            return self._response("Top 10 siniestros con mayor posible riesgo:\n" + "\n".join(lines), top["claim_id"].tolist())

        if "proveedores" in q:
            ranking = self.claims[self.claims["risk_level"].isin(["Medio", "Alto"])].groupby("provider_name").agg(
                alertas=("claim_id", "count"),
                score_promedio=("risk_score", "mean"),
            ).sort_values(["alertas", "score_promedio"], ascending=False).head(8)
            text = "\n".join([f"{idx}: {int(row.alertas)} alertas, score promedio {row.score_promedio:.1f}" for idx, row in ranking.iterrows()])
            return self._response("Proveedores con mayor concentracion de alertas de revision:\n" + text)

        if "ciudades" in q or "casos rojos" in q:
            city = self.claims[self.claims["risk_level"] == "Alto"].groupby("city")["claim_id"].count().sort_values(ascending=False)
            text = "\n".join([f"{idx}: {count} casos rojos" for idx, count in city.head(8).items()])
            return self._response("Ciudades con mas casos de riesgo alto:\n" + (text or "No hay casos rojos en los datos cargados."))

        if "documentos" in q:
            critical = self.claims[self.claims["risk_level"] == "Alto"]
            missing = critical[critical["missing_count"] > 0][["claim_id", "document_names", "document_statuses"]].head(10)
            lines = [f"{r.claim_id}: {r.document_statuses}" for r in missing.itertuples()]
            return self._response("Documentos a revisar en casos criticos:\n" + ("\n".join(lines) or "No se registran faltantes en casos criticos."))

        if "montos atipicos" in q or "montos atípicos" in q:
            high = self.claims.sort_values("claim_amount", ascending=False).head(10)
            lines = [f"{r.claim_id}: USD {r.claim_amount:,.0f}, score {int(r.risk_score)}" for r in high.itertuples()]
            return self._response("Casos con montos mas altos para revision:\n" + "\n".join(lines), high["claim_id"].tolist())

        if "inicio de la poliza" in q or "inicio de la póliza" in q:
            subset = self.claims[self.claims["rules"].apply(lambda rs: any(r["codigo"] == "POLICY_START_PROXIMITY" for r in rs))].head(10)
            lines = [f"{r.claim_id}: {r.claim_date}, poliza {r.policy_id}, score {int(r.risk_score)}" for r in subset.itertuples()]
            return self._response("Siniestros cercanos al inicio de la poliza:\n" + ("\n".join(lines) or "No se encontraron casos con esa senal."))

        if "patrones" in q:
            return self._response(self._patterns_summary())

        if "resumen ejecutivo" in q:
            return self._response(self.executive_summary())

        if "recomienda" in q or "revisar primero" in q:
            top = self.claims.nlargest(5, "risk_score")
            lines = [f"{r.claim_id}: revisar primero por score {int(r.risk_score)} y accion '{r.recommended_action}'." for r in top.itertuples()]
            return self._response("Priorizacion sugerida para analisis humano:\n" + "\n".join(lines), top["claim_id"].tolist())

        return self._response(
            "Puedo responder con base en los siniestros cargados. Prueba con proveedores con alertas, casos de mayor riesgo, documentos faltantes, montos atipicos o resumen ejecutivo."
        )

    def executive_summary(self) -> str:
        total = len(self.claims)
        high = int((self.claims["risk_level"] == "Alto").sum())
        medium = int((self.claims["risk_level"] == "Medio").sum())
        amount = float(self.claims["claim_amount"].sum())
        top_provider = self.claims.groupby("provider_name")["risk_score"].mean().sort_values(ascending=False).head(1)
        provider_text = f"{top_provider.index[0]} (score promedio {top_provider.iloc[0]:.1f})" if not top_provider.empty else "sin proveedor destacado"
        return (
            f"Resumen ejecutivo CheckIA: se analizaron {total} siniestros sinteticos por USD {amount:,.0f}. "
            f"Hay {high} casos de riesgo alto y {medium} de riesgo medio que requieren revision humana priorizada. "
            f"El proveedor con mayor score promedio es {provider_text}. "
            "La herramienta no acusa fraude ni decide rechazos; organiza senales para el analista."
        )

    def _patterns_summary(self) -> str:
        rules = {}
        for active_rules in self.claims["rules"]:
            for rule in active_rules:
                rules[rule["nombre"]] = rules.get(rule["nombre"], 0) + 1
        top = sorted(rules.items(), key=lambda item: item[1], reverse=True)[:6]
        return "Patrones recurrentes detectados:\n" + "\n".join([f"{name}: {count} casos" for name, count in top])

    @staticmethod
    def _response(text: str, related_claims: list[str] | None = None) -> dict:
        return {
            "answer": text,
            "related_claims": related_claims or [],
            "disclaimer": "Respuesta orientativa basada en datos sinteticos. Requiere analisis humano antes de cualquier decision.",
        }
