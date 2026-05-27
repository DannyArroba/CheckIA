from __future__ import annotations

import pandas as pd

from backend.src.ai_agent.ollama_client import OllamaClient


class ClaimsAgent:
    def __init__(self, claims: pd.DataFrame) -> None:
        self.claims = claims
        self.ollama = OllamaClient()

    def answer(self, question: str) -> dict:
        q = question.lower().strip()
        if not q:
            return self._response("Escribe una pregunta sobre los siniestros cargados para ayudarte con datos del sistema.")

        if "10" in q and "mayor riesgo" in q:
            top = self.claims.nlargest(10, "risk_score")
            lines = [f"{r.claim_id}: score {int(r.risk_score)} ({r.risk_level}) - {r.city}, {r.provider_name}" for r in top.itertuples()]
            return self._response("Top 10 siniestros con mayor posible riesgo:\n" + "\n".join(lines), top["claim_id"].tolist(), "reglas")

        if "proveedores" in q:
            ranking = self.claims[self.claims["risk_level"].isin(["Medio", "Alto"])].groupby("provider_name").agg(
                alertas=("claim_id", "count"),
                score_promedio=("risk_score", "mean"),
            ).sort_values(["alertas", "score_promedio"], ascending=False).head(8)
            text = "\n".join([f"{idx}: {int(row.alertas)} alertas, score promedio {row.score_promedio:.1f}" for idx, row in ranking.iterrows()])
            return self._response("Proveedores con mayor concentración de alertas de revisión:\n" + text, provider="reglas")

        if "ciudades" in q or "casos rojos" in q:
            city = self.claims[self.claims["risk_level"] == "Alto"].groupby("city")["claim_id"].count().sort_values(ascending=False)
            text = "\n".join([f"{idx}: {count} casos rojos" for idx, count in city.head(8).items()])
            return self._response("Ciudades con más casos de riesgo alto:\n" + (text or "No hay casos rojos en los datos cargados."), provider="reglas")

        if "documentos" in q:
            critical = self.claims[self.claims["risk_level"] == "Alto"]
            missing = critical[critical["missing_count"] > 0][["claim_id", "document_names", "document_statuses"]].head(10)
            lines = [f"{r.claim_id}: {r.document_statuses}" for r in missing.itertuples()]
            return self._response("Documentos a revisar en casos críticos:\n" + ("\n".join(lines) or "No se registran faltantes en casos críticos."), missing["claim_id"].tolist(), "reglas")

        if "montos atipicos" in q or "montos atípicos" in q:
            high = self.claims.sort_values("claim_amount", ascending=False).head(10)
            lines = [f"{r.claim_id}: USD {r.claim_amount:,.0f}, score {int(r.risk_score)}" for r in high.itertuples()]
            return self._response("Casos con montos más altos para revisión:\n" + "\n".join(lines), high["claim_id"].tolist(), "reglas")

        if "inicio de la poliza" in q or "inicio de la póliza" in q:
            subset = self.claims[self.claims["rules"].apply(lambda rs: any(r["codigo"] == "POLICY_START_PROXIMITY" for r in rs))].head(10)
            lines = [f"{r.claim_id}: {r.claim_date}, póliza {r.policy_id}, score {int(r.risk_score)}" for r in subset.itertuples()]
            return self._response("Siniestros cercanos al inicio de la póliza:\n" + ("\n".join(lines) or "No se encontraron casos con esa señal."), subset["claim_id"].tolist(), "reglas")

        if "patrones" in q:
            return self._response(self._patterns_summary(), provider="reglas")

        if "resumen ejecutivo" in q:
            return self._response(self.executive_summary(), provider="reglas")

        if "recomienda" in q or "revisar primero" in q:
            top = self.claims.nlargest(5, "risk_score")
            lines = [f"{r.claim_id}: revisar primero por score {int(r.risk_score)} y acción '{r.recommended_action}'." for r in top.itertuples()]
            return self._response("Priorización sugerida para análisis humano:\n" + "\n".join(lines), top["claim_id"].tolist(), "reglas")

        ollama_answer = self._answer_with_ollama(question)
        if ollama_answer:
            safe_answer = self._sanitize_language(ollama_answer)
            return self._response(safe_answer, self._extract_related_claims(safe_answer), "ollama")

        return self._response(
            "Puedo responder con base en los siniestros cargados. Prueba con proveedores con alertas, casos de mayor riesgo, documentos faltantes, montos atípicos o resumen ejecutivo. Ollama no respondió a tiempo, así que mantuve una respuesta segura del sistema.",
            provider="reglas",
        )

    def executive_summary(self) -> str:
        total = len(self.claims)
        high = int((self.claims["risk_level"] == "Alto").sum())
        medium = int((self.claims["risk_level"] == "Medio").sum())
        amount = float(self.claims["claim_amount"].sum())
        top_provider = self.claims.groupby("provider_name")["risk_score"].mean().sort_values(ascending=False).head(1)
        provider_text = f"{top_provider.index[0]} (score promedio {top_provider.iloc[0]:.1f})" if not top_provider.empty else "sin proveedor destacado"
        return (
            f"Resumen ejecutivo CheckIA: se analizaron {total} siniestros sintéticos por USD {amount:,.0f}. "
            f"Hay {high} casos de riesgo alto y {medium} de riesgo medio que requieren revisión humana priorizada. "
            f"El proveedor con mayor score promedio es {provider_text}. "
            "La herramienta no acusa fraude ni decide rechazos; organiza señales para el analista."
        )

    def _patterns_summary(self) -> str:
        rules = {}
        for active_rules in self.claims["rules"]:
            for rule in active_rules:
                rules[rule["nombre"]] = rules.get(rule["nombre"], 0) + 1
        top = sorted(rules.items(), key=lambda item: item[1], reverse=True)[:6]
        return "Patrones recurrentes detectados:\n" + "\n".join([f"{name}: {count} casos" for name, count in top])

    def _answer_with_ollama(self, question: str) -> str | None:
        context = self._compact_context(question)
        prompt = (
            f"Pregunta del analista: {question}\n\n"
            f"Contexto de datos CheckIA:\n{context}\n\n"
            "Responde en máximo 80 palabras, sin markdown extenso. Si recomiendas casos, menciona los IDs CLM exactos."
        )
        return self.ollama.generate(prompt)

    def _compact_context(self, question: str) -> str:
        q = question.lower()
        df = self.claims
        if "document" in q:
            focus = df[df["missing_count"] > 0].nlargest(4, "risk_score")
        elif "proveedor" in q:
            ranking = df.groupby("provider_name").agg(
                alertas=("risk_level", lambda values: int(values.isin(["Medio", "Alto"]).sum())),
                score_promedio=("risk_score", "mean"),
            ).sort_values(["alertas", "score_promedio"], ascending=False).head(6)
            providers = "; ".join([f"{idx}: {int(row.alertas)} alertas, score {row.score_promedio:.1f}" for idx, row in ranking.iterrows()])
            focus = df.nlargest(4, "risk_score")
            return f"{self.executive_summary()}\nRanking proveedores: {providers}\nCasos principales:\n{self._claims_lines(focus)}"
        else:
            focus = df.nlargest(4, "risk_score")

        return (
            f"{self._short_summary()}\n"
            f"Casos relevantes:\n{self._claims_lines(focus)}"
        )

    def _short_summary(self) -> str:
        high = int((self.claims["risk_level"] == "Alto").sum())
        medium = int((self.claims["risk_level"] == "Medio").sum())
        return f"Dataset: {len(self.claims)} siniestros sintéticos; {high} alto riesgo; {medium} riesgo medio."

    @staticmethod
    def _claims_lines(df: pd.DataFrame) -> str:
        lines = []
        for row in df.itertuples():
            rule_names = ", ".join([rule["nombre"] for rule in row.rules[:2]]) if row.rules else "sin reglas fuertes"
            lines.append(
                f"{row.claim_id} | {row.line} | {row.coverage} | {row.city} | {row.provider_name} | "
                f"monto USD {row.claim_amount:,.0f} | score {int(row.risk_score)} {row.risk_level} | señales: {rule_names}"
            )
        return "\n".join(lines)

    def _extract_related_claims(self, text: str) -> list[str]:
        ids = set(self.claims["claim_id"].tolist())
        return sorted([claim_id for claim_id in ids if claim_id in text])

    @staticmethod
    def _sanitize_language(text: str) -> str:
        replacements = {
            "probabilidad de fraude": "posible riesgo",
            "riesgo de fraude": "posible riesgo",
            "fraude": "posible riesgo",
            "fraudulento": "con señales de revisión",
            "sospechoso": "inusual",
            "culpable": "caso a revisar",
        }
        safe = text
        for source, target in replacements.items():
            safe = safe.replace(source, target).replace(source.capitalize(), target.capitalize())
        if not safe.endswith((".", "!", "?")):
            safe = safe.rstrip(" ,;:") + "."
        return safe

    @staticmethod
    def _response(text: str, related_claims: list[str] | None = None, provider: str = "reglas") -> dict:
        return {
            "answer": text,
            "related_claims": related_claims or [],
            "provider": provider,
            "disclaimer": "Respuesta orientativa basada en datos sintéticos. Requiere análisis humano antes de cualquier decisión.",
        }
