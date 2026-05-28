from __future__ import annotations

import re

import pandas as pd

from backend.src.ai_agent.ollama_client import OllamaClient


REVIEW_LABELS = {
    "pendiente": "Pendiente",
    "bajo_observacion": "Bajo observación",
    "documentacion_solicitada": "Documentación solicitada",
    "revisado_sin_alerta": "Revisado sin alerta adicional",
    "derivado_analista": "Derivado a analista",
}


class ClaimsAgent:
    def __init__(self, claims: pd.DataFrame, review_context: list[dict] | None = None) -> None:
        self.claims = claims
        self.review_context = review_context or []
        self.ollama = OllamaClient()

    def answer(self, question: str) -> dict:
        q = question.lower().strip()
        style = self._response_style(question)
        if not q:
            return self._response("Claro. Pregúntame por casos críticos, proveedores, documentos o seguimientos.", suggestions=self._suggestions_for(q))
        specific_claim = self._specific_claim_response(q)
        if specific_claim:
            return specific_claim
        latest_cases = self._latest_cases_response(q)
        if latest_cases:
            return latest_cases
        if self._asks_complete_analysis(q):
            return self._response(self.complete_analysis(), self.claims.nlargest(5, "risk_score")["claim_id"].tolist(), "reglas", self._suggestions_for(q))
        if style == "short" and not self._has_data_intent(q):
            return self._response(self._local_open_answer(q, style), suggestions=self._suggestions_for(q))

        if self._asks_review_status(q):
            return self._response(self._review_summary(style), self._review_claim_ids(), "reglas", self._suggestions_for(q))

        if self._asks_top_risk(q):
            top = self.claims.nlargest(10, "risk_score")
            lines = [f"{r.claim_id}: score {int(r.risk_score)} ({r.risk_level}) - {r.city}, {r.provider_name}" for r in top.itertuples()]
            return self._response("Top 10 por posible riesgo:\n" + "\n".join(lines), top["claim_id"].tolist(), "reglas", ["Explícame el primero", "Proveedores con alertas"])

        if "proveedor" in q:
            ranking = self.claims[self.claims["risk_level"].isin(["Medio", "Alto"])].groupby("provider_name").agg(
                alertas=("claim_id", "count"),
                score_promedio=("risk_score", "mean"),
            ).sort_values(["alertas", "score_promedio"], ascending=False).head(8)
            text = "\n".join([f"{idx}: {int(row.alertas)} alertas, score promedio {row.score_promedio:.1f}" for idx, row in ranking.iterrows()])
            return self._response("Concentración por proveedor:\n" + text, provider="reglas", suggestions=self._suggestions_for(q))

        if "ciudad" in q or "casos rojos" in q:
            city = self.claims[self.claims["risk_level"] == "Alto"].groupby("city")["claim_id"].count().sort_values(ascending=False)
            text = "\n".join([f"{idx}: {count} casos rojos" for idx, count in city.head(8).items()])
            return self._response("Ciudades con más casos de riesgo alto:\n" + (text or "No hay casos rojos en los datos cargados."), provider="reglas", suggestions=self._suggestions_for(q))

        if "document" in q:
            critical = self.claims[self.claims["risk_level"] == "Alto"]
            missing = critical[critical["missing_count"] > 0][["claim_id", "document_statuses"]].head(10)
            lines = [f"{r.claim_id}: {r.document_statuses}" for r in missing.itertuples()]
            return self._response("Documentos a revisar:\n" + ("\n".join(lines) or "No se registran faltantes en casos críticos."), missing["claim_id"].tolist(), "reglas", self._suggestions_for(q))

        if "monto" in q or "atipic" in q:
            high = self.claims.sort_values("claim_amount", ascending=False).head(10)
            lines = [f"{r.claim_id}: USD {r.claim_amount:,.0f}, score {int(r.risk_score)}" for r in high.itertuples()]
            return self._response("Montos más altos:\n" + "\n".join(lines), high["claim_id"].tolist(), "reglas", self._suggestions_for(q))

        if "inicio de la poliza" in q or "inicio de la póliza" in q:
            subset = self.claims[self.claims["rules"].apply(lambda rs: any(r["codigo"] == "POLICY_START_PROXIMITY" for r in rs))].head(10)
            lines = [f"{r.claim_id}: {r.claim_date}, póliza {r.policy_id}, score {int(r.risk_score)}" for r in subset.itertuples()]
            return self._response("Cercanos al inicio de póliza:\n" + ("\n".join(lines) or "No encontré casos con esa señal."), subset["claim_id"].tolist(), "reglas", self._suggestions_for(q))

        if "patron" in q or "patrón" in q:
            return self._response(self._patterns_summary(style), provider="reglas", suggestions=self._suggestions_for(q))

        if "resumen" in q or "ejecutivo" in q:
            return self._response(self.executive_summary(style), provider="reglas", suggestions=self._suggestions_for(q))

        if "recomienda" in q or "revisar primero" in q or "prioriza" in q:
            top = self.claims.nlargest(5, "risk_score")
            lines = [f"{r.claim_id}: score {int(r.risk_score)}, {r.recommended_action}" for r in top.itertuples()]
            return self._response("Revisaría primero:\n" + "\n".join(lines), top["claim_id"].tolist(), "reglas", self._suggestions_for(q))

        ollama_answer = self._answer_with_ollama(question, style)
        if ollama_answer:
            safe_answer = self._validate_claim_references(self._sanitize_language(ollama_answer))
            return self._response(safe_answer, self._extract_related_claims(safe_answer), "ollama", self._suggestions_for(q))

        return self._response(self._local_open_answer(q, style), self.claims.nlargest(3, "risk_score")["claim_id"].tolist(), "reglas", self._suggestions_for(q))

    def executive_summary(self, style: str = "normal") -> str:
        total = len(self.claims)
        high = int((self.claims["risk_level"] == "Alto").sum())
        medium = int((self.claims["risk_level"] == "Medio").sum())
        amount = float(self.claims["claim_amount"].sum())
        if style == "short":
            return f"{total} siniestros: {high} altos, {medium} medios. Monto total: USD {amount:,.0f}."
        top_provider = self.claims.groupby("provider_name")["risk_score"].mean().sort_values(ascending=False).head(1)
        provider_text = f"{top_provider.index[0]} (score promedio {top_provider.iloc[0]:.1f})" if not top_provider.empty else "sin proveedor destacado"
        return (
            f"Se analizaron {total} siniestros sintéticos por USD {amount:,.0f}. "
            f"Hay {high} casos de riesgo alto y {medium} de riesgo medio. "
            f"Proveedor con mayor score promedio: {provider_text}."
        )

    def _specific_claim_response(self, q: str) -> dict | None:
        claim_ids = sorted(set(re.findall(r"clm-\d{4,}", q)))
        if not claim_ids:
            return None
        requested = [claim_id.upper() for claim_id in claim_ids]
        matches = self.claims[self.claims["claim_id"].isin(requested)]
        if matches.empty:
            top_ids = ", ".join(self.claims.nlargest(3, "risk_score")["claim_id"].tolist())
            return self._response(
                f"No encontré esos IDs en el dataset cargado. IDs reales sugeridos: {top_ids}.",
                [],
                "reglas",
                ["Top 10 casos", "Resumen ejecutivo"],
            )

        lines = []
        for row in matches.itertuples():
            rules = ", ".join([rule["nombre"] for rule in row.rules[:4]]) if row.rules else "sin reglas fuertes registradas"
            documents = getattr(row, "document_statuses", "sin detalle documental")
            amount = getattr(row, "claim_amount", None)
            amount_text = f"USD {amount:,.0f}" if amount is not None else "sin monto disponible"
            lines.append(
                f"{row.claim_id}: score {int(row.risk_score)} ({row.risk_level}), ciudad {row.city}, proveedor {row.provider_name}, monto {amount_text}. "
                f"Señales: {rules}. Documentos: {documents}. Acción recomendada: {row.recommended_action}."
            )
        related = matches["claim_id"].tolist()
        return self._response(
            "\n".join(lines),
            related,
            "reglas",
            ["Explícame las señales", "Ver documentos", "Resumen ejecutivo"],
        )

    def _latest_cases_response(self, q: str) -> dict | None:
        if not re.search(r"\b(ultimos|últimos|recientes|nuevos)\b", q):
            return None
        if not re.search(r"\b(caso|casos|siniestro|siniestros)\b", q):
            return None
        limit_match = re.search(r"\b(\d{1,2})\b", q)
        limit = int(limit_match.group(1)) if limit_match else 5
        limit = max(1, min(limit, 15))
        df = self.claims.copy()
        if "claim_date" in df.columns:
            df["_sort_date"] = pd.to_datetime(df["claim_date"], errors="coerce")
            df = df.sort_values(["_sort_date", "claim_id"], ascending=[False, False])
        else:
            df = df.sort_values("claim_id", ascending=False)
        latest = df.head(limit)
        lines = [
            f"{row.claim_id}: fecha {row.claim_date}, score {int(row.risk_score)} ({row.risk_level}), {row.city}, {row.provider_name}"
            for row in latest.itertuples()
        ]
        return self._response(
            f"Últimos {len(latest)} casos por fecha de siniestro:\n" + "\n".join(lines),
            latest["claim_id"].tolist(),
            "reglas",
            ["Ver detalle del primero", "Top 10 casos", "Resumen ejecutivo"],
        )

    def complete_analysis(self) -> str:
        total = len(self.claims)
        high = int((self.claims["risk_level"] == "Alto").sum())
        medium = int((self.claims["risk_level"] == "Medio").sum())
        amount = float(self.claims["claim_amount"].sum())
        top_cases = self.claims.nlargest(5, "risk_score")
        case_lines = []
        for row in top_cases.itertuples():
            rules = ", ".join([rule["nombre"] for rule in row.rules[:2]]) if row.rules else "sin reglas fuertes"
            case_lines.append(
                f"- {row.claim_id} | score {int(row.risk_score)} | {row.risk_level} | {row.city} | {row.provider_name} | {rules}"
            )

        provider_ranking = self.claims[self.claims["risk_level"].isin(["Medio", "Alto"])].groupby("provider_name").agg(
            alertas=("claim_id", "count"),
            score_promedio=("risk_score", "mean"),
        ).sort_values(["alertas", "score_promedio"], ascending=False).head(5)
        provider_lines = [
            f"- {idx}: {int(row.alertas)} alertas, score promedio {row.score_promedio:.1f}"
            for idx, row in provider_ranking.iterrows()
        ]

        city_ranking = self.claims[self.claims["risk_level"] == "Alto"].groupby("city")["claim_id"].count().sort_values(ascending=False).head(5)
        city_lines = [f"- {idx}: {count} casos altos" for idx, count in city_ranking.items()]

        rules = {}
        for active_rules in self.claims["rules"]:
            for rule in active_rules:
                rules[rule["nombre"]] = rules.get(rule["nombre"], 0) + 1
        rule_lines = [f"- {name}: {count} casos" for name, count in sorted(rules.items(), key=lambda item: item[1], reverse=True)[:5]]

        missing_docs = self.claims[self.claims["missing_count"] > 0][["claim_id", "missing_count", "document_statuses"]].head(5)
        doc_lines = [
            f"- {row.claim_id}: {int(row.missing_count)} documento(s) faltante(s) o a revisar ({row.document_statuses})"
            for row in missing_docs.itertuples()
        ]

        return (
            "Análisis completo:\n"
            f"Resumen ejecutivo: {total} siniestros analizados, {high} altos, {medium} medios, monto total USD {amount:,.0f}.\n\n"
            "Casos prioritarios:\n" + ("\n".join(case_lines) or "- No hay casos prioritarios disponibles.") + "\n\n"
            "Señales principales:\n" + ("\n".join(rule_lines) or "- No hay reglas activadas registradas.") + "\n\n"
            "Concentración por proveedor:\n" + ("\n".join(provider_lines) or "- No hay concentración relevante en proveedores.") + "\n\n"
            "Ciudades con riesgo alto:\n" + ("\n".join(city_lines) or "- No hay casos altos por ciudad.") + "\n\n"
            "Documentación y montos:\n" + ("\n".join(doc_lines) or "- No hay faltantes documentales relevantes en los datos cargados.") + "\n\n"
            "Próximos pasos: revisar primero los casos de mayor score, validar documentos y contrastar las señales con evidencia del expediente."
        )

    def _review_summary(self, style: str = "normal") -> str:
        if not self.review_context:
            return "Aún no hay casos con seguimiento humano registrado."
        counts: dict[str, int] = {}
        for item in self.review_context:
            label = REVIEW_LABELS.get(item.get("status"), item.get("status", "Sin estado"))
            counts[label] = counts.get(label, 0) + 1
        totals = ", ".join([f"{label}: {count}" for label, count in counts.items()])
        if style == "short":
            return f"Seguimiento registrado: {totals}."
        lines = [
            f"{item['claim_id']}: {REVIEW_LABELS.get(item.get('status'), item.get('status'))}"
            + (f" - {item['note']}" if item.get("note") else "")
            for item in self.review_context[:8]
        ]
        return f"Seguimiento humano:\nResumen: {totals}.\nCasos recientes:\n" + "\n".join(lines)

    def _patterns_summary(self, style: str = "normal") -> str:
        rules = {}
        for active_rules in self.claims["rules"]:
            for rule in active_rules:
                rules[rule["nombre"]] = rules.get(rule["nombre"], 0) + 1
        top = sorted(rules.items(), key=lambda item: item[1], reverse=True)[:6]
        if style == "short":
            return "Patrones principales: " + ", ".join([f"{name} ({count})" for name, count in top[:3]])
        return "Patrones recurrentes:\n" + "\n".join([f"{name}: {count} casos" for name, count in top])

    def _answer_with_ollama(self, question: str, style: str) -> str | None:
        max_words = {"short": 45, "normal": 90, "detailed": 160}[style]
        prompt = (
            f"Pregunta: {question}\n"
            f"Datos: {self._compact_context(question, style)}\n"
            f"Limite: maximo {max_words} palabras."
        )
        return self.ollama.generate(prompt)

    def _compact_context(self, question: str, style: str = "normal") -> str:
        q = question.lower()
        claim_ids = re.findall(r"clm-\d{4,}", q)
        if claim_ids:
            focus = self.claims[self.claims["claim_id"].str.lower().isin(claim_ids)]
            if focus.empty:
                focus = self.claims.nlargest(3, "risk_score")
        elif style == "detailed" or self._asks_complete_analysis(q):
            focus = self.claims.nlargest(8, "risk_score")
        else:
            focus = self.claims.nlargest(3, "risk_score")

        parts = [self._short_summary()]
        if style == "detailed" or any(term in q for term in ["proveedor", "ciudad", "ranking", "concentra"]):
            parts.append(self._compact_rankings())
        if self.review_context and any(term in q for term in ["seguimiento", "estado", "observacion", "observación"]):
            parts.append(self._compact_review_context())
        parts.append("Casos: " + self._claims_lines(focus))
        return " ".join(parts)

    def _compact_rankings(self) -> str:
        providers = self.claims[self.claims["risk_level"].isin(["Medio", "Alto"])].groupby("provider_name").agg(
            alertas=("claim_id", "count"),
            score_promedio=("risk_score", "mean"),
        ).sort_values(["alertas", "score_promedio"], ascending=False).head(3)
        provider_text = "; ".join([f"{idx} {int(row.alertas)} alertas score {row.score_promedio:.1f}" for idx, row in providers.iterrows()])
        cities = self.claims[self.claims["risk_level"] == "Alto"].groupby("city")["claim_id"].count().sort_values(ascending=False).head(3)
        city_text = "; ".join([f"{idx} {count} altos" for idx, count in cities.items()])
        return f"Ranking proveedores: {provider_text or 'sin datos'}. Ranking ciudades: {city_text or 'sin datos'}."

    def _short_summary(self) -> str:
        high = int((self.claims["risk_level"] == "Alto").sum())
        medium = int((self.claims["risk_level"] == "Medio").sum())
        return f"Dataset: {len(self.claims)} siniestros; {high} alto riesgo; {medium} riesgo medio."

    def _compact_review_context(self) -> str:
        if not self.review_context:
            return "Seguimiento humano: sin registros."
        lines = [f"{item['claim_id']} estado {item['status']}" for item in self.review_context[:5]]
        return "Seguimiento humano: " + "; ".join(lines)

    @staticmethod
    def _claims_lines(df: pd.DataFrame) -> str:
        lines = []
        for row in df.itertuples():
            rule_names = ", ".join([rule["nombre"] for rule in row.rules[:2]]) if row.rules else "sin reglas fuertes"
            lines.append(f"{row.claim_id}|{row.city}|{row.provider_name}|score {int(row.risk_score)} {row.risk_level}|{rule_names}")
        return "; ".join(lines)

    def _local_open_answer(self, q: str, style: str = "normal") -> str:
        if re.search(r"\b(hola|buenas|hey|qué tal|que tal)\b", q):
            return "Hola. Puedo ayudarte con casos críticos, proveedores, documentos, montos o seguimientos."
        top = self.claims.nlargest(3, "risk_score")
        high = int((self.claims["risk_level"] == "Alto").sum())
        medium = int((self.claims["risk_level"] == "Medio").sum())
        examples = ", ".join([f"{r.claim_id} ({int(r.risk_score)})" for r in top.itertuples()])
        if style == "short":
            return f"Hay {high} casos altos y {medium} medios. Prioriza {examples}."
        return f"Hay {high} casos de riesgo alto y {medium} de riesgo medio. Para empezar, revisaría {examples}. Puedes pedirme detalle por proveedor, documentos o seguimiento."

    def _asks_top_risk(self, q: str) -> bool:
        return (
            ("mayor riesgo" in q)
            or ("top" in q and ("riesgo" in q or "casos" in q))
            or ("primeros" in q and ("casos" in q or "siniestros" in q))
            or ("10" in q and ("casos" in q or "siniestros" in q))
        )

    @staticmethod
    def _has_data_intent(q: str) -> bool:
        terms = [
            "caso", "casos", "siniestro", "siniestros", "riesgo", "proveedor", "proveedores",
            "documento", "documentos", "monto", "montos", "ciudad", "ciudades", "seguimiento",
            "estado", "póliza", "poliza", "reporte", "score", "alerta", "resumen", "top"
        ]
        return any(term in q for term in terms)

    @staticmethod
    def _asks_complete_analysis(q: str) -> bool:
        return any(term in q for term in [
            "analisis completo",
            "análisis completo",
            "analiza a fondo",
            "revision integral",
            "revisión integral",
            "informe completo",
            "reporte completo",
            "diagnostico completo",
            "diagnóstico completo",
        ])

    @staticmethod
    def _asks_review_status(q: str) -> bool:
        return any(term in q for term in ["seguimiento", "observacion", "observación", "proceso", "estado", "derivado"])

    @staticmethod
    def _response_style(question: str) -> str:
        words = question.strip().split()
        q = question.lower()
        if len(words) <= 5 or q in {"hola", "buenas", "ok", "gracias"}:
            return "short"
        if any(term in q for term in ["detalla", "explica", "por qué", "porque", "analiza", "profundiza"]):
            return "detailed"
        return "normal"

    @staticmethod
    def _suggestions_for(q: str) -> list[str]:
        if "proveedor" in q:
            return ["Top 10 casos", "Ciudades con casos rojos"]
        if "document" in q:
            return ["Casos críticos", "Seguimiento humano"]
        if "seguimiento" in q or "estado" in q:
            return ["Casos bajo observación", "Top riesgo"]
        return ["Top 10 casos", "Proveedores con alertas", "Resumen ejecutivo"]

    def _review_claim_ids(self) -> list[str]:
        return [item["claim_id"] for item in self.review_context if item.get("claim_id")]

    def _extract_related_claims(self, text: str) -> list[str]:
        ids = set(self.claims["claim_id"].tolist())
        return sorted([claim_id for claim_id in ids if claim_id in text])

    def _validate_claim_references(self, text: str) -> str:
        valid_ids = set(self.claims["claim_id"].tolist())
        invalid = sorted(set(re.findall(r"CLM-\d{4,}", text)) - valid_ids)
        if not invalid:
            return text
        cleaned = text
        for claim_id in invalid:
            cleaned = cleaned.replace(claim_id, "un caso relevante del ranking")
        top_ids = ", ".join(self.claims.nlargest(3, "risk_score")["claim_id"].tolist())
        return cleaned + f"\n\nIDs reales sugeridos: {top_ids}."

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
        return safe if safe.endswith((".", "!", "?")) else safe.rstrip(" ,;:") + "."

    @staticmethod
    def _response(text: str, related_claims: list[str] | None = None, provider: str = "reglas", suggestions: list[str] | None = None) -> dict:
        return {
            "answer": text,
            "related_claims": related_claims or [],
            "provider": provider,
            "suggestions": suggestions or [],
            "disclaimer": "Respuesta orientativa basada en datos sintéticos. Requiere análisis humano antes de cualquier decisión.",
        }
