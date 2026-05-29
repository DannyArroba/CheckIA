from __future__ import annotations

import json
import re
import shutil
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from pypdf import PdfReader

from backend.src.services.database_service import get_connection


UPLOAD_DIR = Path("backend/data/hackia_uploads")
PDF_DIR = UPLOAD_DIR / "pdfs"
EXCEL_DIR = UPLOAD_DIR / "excel"

SHEET_ALIASES = {
    "siniestros": "1_Siniestros",
    "polizas": "2_Polizas",
    "asegurados": "3_Asegurados",
    "proveedores": "4_Proveedores",
    "documentos": "5_Documentos",
    "indice": "6_Indice_Documentos",
}
REQUIRED_SHEETS = {key: value for key, value in SHEET_ALIASES.items() if key != "indice"}


def ensure_hackia_schema() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS siniestros (
                  id_siniestro VARCHAR(30) PRIMARY KEY,
                  id_poliza VARCHAR(30), id_asegurado VARCHAR(30), fecha_siniestro DATE,
                  fecha_reporte DATE, ramo VARCHAR(80), placa VARCHAR(30), ciudad VARCHAR(100),
                  sucursal VARCHAR(100), id_proveedor VARCHAR(30), descripcion_evento TEXT,
                  docs_completos BOOLEAN, proveedor_lista_restrictiva BOOLEAN,
                  dias_desde_inicio_poliza INT, dias_hasta_fin_poliza INT, reclamos_previos INT,
                  suma_asegurada DECIMAL(14,2), similitud_narrativa_max DECIMAL(8,4),
                  numero_parte_policial VARCHAR(80), monto_reclamado DECIMAL(14,2),
                  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
                """
            )
            _ensure_column(cursor, "siniestros", "cobertura", "VARCHAR(120)")
            _ensure_column(cursor, "siniestros", "dias_ocurrencia_reporte", "INT")
            _ensure_column(cursor, "siniestros", "monto_estimado", "DECIMAL(14,2)")
            _ensure_column(cursor, "siniestros", "monto_pagado", "DECIMAL(14,2)")
            _ensure_column(cursor, "siniestros", "estado", "VARCHAR(80)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS polizas (
                  id_poliza VARCHAR(30) PRIMARY KEY, id_asegurado VARCHAR(30), ramo VARCHAR(80),
                  fecha_inicio DATE, fecha_fin DATE, suma_asegurada DECIMAL(14,2),
                  prima_anual DECIMAL(14,2), canal_venta VARCHAR(100), estado_poliza VARCHAR(80)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS asegurados (
                  id_asegurado VARCHAR(30) PRIMARY KEY, nombres_asegurado VARCHAR(180),
                  segmento VARCHAR(80), ciudad VARCHAR(100), antiguedad VARCHAR(80),
                  polizas_activas INT, reclamos_ultimos_12_meses INT,
                  reclamos_historico_total INT, reclamos_rc_sin_tercero INT,
                  perfil_riesgo_historico VARCHAR(80)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS proveedores_hackia (
                  id_proveedor VARCHAR(30) PRIMARY KEY, nombre_proveedor VARCHAR(180),
                  tipo VARCHAR(80), ciudad VARCHAR(100), siniestros_asociados INT,
                  en_lista_restrictiva BOOLEAN, motivo_restriccion TEXT,
                  observacion_proveedor TEXT, promedio_monto DECIMAL(14,2)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS documentos (
                  id_documento VARCHAR(30) PRIMARY KEY, id_siniestro VARCHAR(30),
                  tipo_documento VARCHAR(120), nombre_archivo_pdf VARCHAR(255),
                  pdf_no_encontrado BOOLEAN NOT NULL DEFAULT FALSE,
                  documento_no_listado_en_excel BOOLEAN NOT NULL DEFAULT FALSE,
                  ruta_archivo VARCHAR(500), created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_documentos_siniestro (id_siniestro)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS documentos_extraidos (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY, id_documento VARCHAR(30), id_siniestro VARCHAR(30),
                  tipo_documento VARCHAR(120), nombre_archivo VARCHAR(255), ruta_archivo VARCHAR(500),
                  metodo_extraccion VARCHAR(40), texto_extraido LONGTEXT, campos_extraidos JSON,
                  ocr_usado BOOLEAN NOT NULL DEFAULT FALSE,
                  documento_no_listado_en_excel BOOLEAN NOT NULL DEFAULT FALSE,
                  pdf_no_encontrado BOOLEAN NOT NULL DEFAULT FALSE,
                  procesado_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE KEY uk_doc_file (nombre_archivo),
                  INDEX idx_extraidos_siniestro (id_siniestro)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS facturas (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY, id_documento VARCHAR(30), id_siniestro VARCHAR(30),
                  numero_factura VARCHAR(80), fecha DATE, taller_proveedor VARCHAR(180), ruc VARCHAR(20),
                  cliente VARCHAR(180), placa VARCHAR(30), vehiculo VARCHAR(160), subtotal DECIMAL(14,2),
                  iva DECIMAL(14,2), total_pagar DECIMAL(14,2), descripciones_reparacion TEXT,
                  documento_alterado BOOLEAN NOT NULL DEFAULT FALSE, caso_marcado VARCHAR(60),
                  INDEX idx_facturas_siniestro (id_siniestro)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS partes_policiales (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY, id_documento VARCHAR(30), id_siniestro VARCHAR(30),
                  numero_parte_policial VARCHAR(80), fecha DATE, lugar VARCHAR(180),
                  vehiculos_involucrados TEXT, narrativa_accidente TEXT, autoridad_agente VARCHAR(180),
                  observaciones_relevantes TEXT, INDEX idx_partes_siniestro (id_siniestro)
                )
                """
            )
            _ensure_column(cursor, "partes_policiales", "hora", "VARCHAR(40)")
            _ensure_column(cursor, "partes_policiales", "placa", "VARCHAR(30)")
            _ensure_column(cursor, "partes_policiales", "marca", "VARCHAR(80)")
            _ensure_column(cursor, "partes_policiales", "modelo", "VARCHAR(80)")
            _ensure_column(cursor, "partes_policiales", "motor", "VARCHAR(120)")
            _ensure_column(cursor, "partes_policiales", "chasis", "VARCHAR(120)")
            _ensure_column(cursor, "partes_policiales", "tipo_accidente", "VARCHAR(100)")
            _ensure_column(cursor, "partes_policiales", "consecuencias", "VARCHAR(180)")
            _ensure_column(cursor, "partes_policiales", "clima", "VARCHAR(80)")
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS declaraciones_accidente (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY, id_documento VARCHAR(30), id_siniestro VARCHAR(30),
                  asegurado VARCHAR(180), telefono VARCHAR(80), direccion VARCHAR(220), poliza VARCHAR(80),
                  placa VARCHAR(30), marca VARCHAR(80), modelo VARCHAR(80), color VARCHAR(60), chasis VARCHAR(120),
                  motor VARCHAR(120), fecha_accidente DATE, hora VARCHAR(40), lugar VARCHAR(180),
                  velocidad VARCHAR(80), descripcion_accidente TEXT, responsable_conductor VARCHAR(180),
                  datos_contrario TEXT, intervencion_autoridades VARCHAR(120), lugar_asistencia_medica VARCHAR(180),
                  INDEX idx_declaraciones_siniestro (id_siniestro)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS alertas_fraude (
                  id_alerta BIGINT AUTO_INCREMENT PRIMARY KEY, id_siniestro VARCHAR(30),
                  tipo_alerta VARCHAR(120), severidad ENUM('baja','media','alta','critica') NOT NULL,
                  explicacion TEXT, fuente_evidencia VARCHAR(80), campo_detectado VARCHAR(120),
                  valor_esperado TEXT, valor_encontrado TEXT,
                  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_alertas_siniestro (id_siniestro)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS analisis_fraude (
                  id_siniestro VARCHAR(30) PRIMARY KEY, puntaje_riesgo INT NOT NULL,
                  nivel_riesgo ENUM('Bajo','Medio','Alto','Critico') NOT NULL,
                  explicacion TEXT, factores JSON,
                  calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS hackia_import_logs (
                  id BIGINT AUTO_INCREMENT PRIMARY KEY, tipo VARCHAR(60), mensaje TEXT,
                  detalle JSON, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        connection.commit()


def _ensure_column(cursor, table: str, column: str, definition: str) -> None:
    cursor.execute(f"SHOW COLUMNS FROM {table} LIKE %s", (column,))
    if not cursor.fetchone():
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def import_excel_workbook(path: Path) -> dict:
    ensure_hackia_schema()
    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    found = {_canonical_sheet(name): name for name in sheets}
    missing = [expected for expected in REQUIRED_SHEETS.values() if _canonical_sheet(expected) not in found]
    if missing:
        raise ValueError(f"Excel incompleto. Faltan hojas: {', '.join(missing)}")

    frames = {key: _clean_frame(sheets[found[_canonical_sheet(sheet)]]) for key, sheet in REQUIRED_SHEETS.items()}
    frames["indice"] = _clean_frame(sheets[found[_canonical_sheet(SHEET_ALIASES["indice"])]]) if _canonical_sheet(SHEET_ALIASES["indice"]) in found else pd.DataFrame()
    counts = {
        "siniestros": _import_siniestros(frames["siniestros"]),
        "polizas": _import_polizas(frames["polizas"]),
        "asegurados": _import_asegurados(frames["asegurados"]),
        "proveedores": _import_proveedores(frames["proveedores"]),
        "documentos": _import_documentos(frames["documentos"], frames["indice"]),
    }
    _mark_missing_pdfs()
    analysis = recalculate_hackia_analysis()
    _log("excel", "Excel importado correctamente", {"archivo": path.name, "registros": counts, "analisis": analysis})
    return {"accepted": True, "file": path.name, "sheets": list(sheets.keys()), "records": counts, "analysis": analysis}


def clear_legacy_demo_data() -> dict:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            for table in [
                "claim_rule_results",
                "claim_risk_results",
                "claim_documents",
                "claim_review_actions",
                "claims",
                "policies",
                "customers",
                "providers",
            ]:
                cursor.execute(f"DELETE FROM {table}")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        connection.commit()
    _log("limpieza", "Datos demo anteriores eliminados", {"tablas": ["claims", "policies", "customers", "providers", "claim_documents"]})
    return {"cleared": True, "message": "Datos demo anteriores eliminados. El flujo HackIAthon queda como fuente principal."}


def clear_hackia_data() -> dict:
    ensure_hackia_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            for table in [
                "alertas_fraude",
                "analisis_fraude",
                "facturas",
                "partes_policiales",
                "declaraciones_accidente",
                "documentos_extraidos",
                "documentos",
                "siniestros",
                "polizas",
                "asegurados",
                "proveedores_hackia",
            ]:
                cursor.execute(f"DELETE FROM {table}")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        connection.commit()
    _log("limpieza", "Datos HackIAthon eliminados", {})
    return {"cleared": True, "message": "Datos HackIAthon eliminados."}


def process_pdf_batch(paths: list[Path]) -> dict:
    ensure_hackia_schema()
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    stats = {
        "pdfs_procesados": 0,
        "ocr_usado": 0,
        "vinculados": 0,
        "rechazados": 0,
        "sin_relacion": 0,
        "duplicados": 0,
        "reprocesados": 0,
        "errores": 0,
    }
    details = []
    for source_path in paths:
        try:
            filename = source_path.name
            target = PDF_DIR / filename
            existing = _fetch_one("SELECT id FROM documentos_extraidos WHERE nombre_archivo=%s", (filename,))
            if existing:
                stats["duplicados"] += 1
                stats["reprocesados"] += 1

            text, method, ocr_used = _extract_pdf_text(source_path)
            ids = _merge_detected_ids(_ids_from_filename(filename), _ids_from_text(text))
            doc_type = _detect_document_type(filename, text)
            fields = _extract_fields(text, doc_type, filename)
            id_siniestro = fields.get("id_siniestro") or ids.get("id_siniestro")
            id_documento = fields.get("id_documento") or ids.get("id_documento")

            if not id_siniestro and not id_documento:
                _reject_pdf(stats, details, filename, "No se detecto ID de siniestro SIN-xxxx ni ID de documento DOC-xxxx en el nombre o contenido del PDF.")
                continue

            excel_doc, rejection_reason = _validate_pdf_against_excel(id_documento, id_siniestro, filename, doc_type)
            if not excel_doc:
                _reject_pdf(stats, details, filename, rejection_reason, id_siniestro, id_documento, doc_type)
                continue

            id_documento = excel_doc.get("id_documento") or id_documento
            id_siniestro = excel_doc.get("id_siniestro") or id_siniestro
            if source_path.resolve() != target.resolve():
                shutil.copy2(source_path, target)

            _upsert_document(id_documento, id_siniestro, doc_type, filename, str(target), False)
            _insert_extracted(id_documento, id_siniestro, doc_type, filename, target, method, text, fields, ocr_used, False)
            _insert_typed_document(id_documento, id_siniestro, doc_type, fields)
            stats["pdfs_procesados"] += 1
            stats["ocr_usado"] += 1 if ocr_used else 0
            stats["vinculados"] += 1
            details.append({"archivo": filename, "id_siniestro": id_siniestro, "id_documento": id_documento, "tipo": doc_type, "metodo": method})
        except Exception as exc:
            stats["errores"] += 1
            details.append({"archivo": source_path.name, "error": str(exc)})

    _mark_missing_pdfs()
    analysis = recalculate_hackia_analysis()
    _log("pdf", "PDFs procesados", {"stats": stats, "detalles": details[:40], "analisis": analysis})
    return {"accepted": True, "stats": stats, "details": details, "analysis": analysis}


def _process_pdf_batch_legacy(paths: list[Path]) -> dict:
    ensure_hackia_schema()
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    stats = {
        "pdfs_procesados": 0,
        "ocr_usado": 0,
        "vinculados": 0,
        "rechazados": 0,
        "sin_relacion": 0,
        "duplicados": 0,
        "reprocesados": 0,
        "errores": 0,
    }
    details = []
    for source_path in paths:
        try:
            filename = source_path.name
            target = PDF_DIR / filename
            existing = _fetch_one("SELECT id FROM documentos_extraidos WHERE nombre_archivo=%s", (filename,))
            if existing:
                stats["duplicados"] += 1
                stats["reprocesados"] += 1
            text, method, ocr_used = _extract_pdf_text(source_path)
            ids = _ids_from_filename(filename) | _ids_from_text(text)
            doc_type = _detect_document_type(filename, text)
            fields = _extract_fields(text, doc_type, filename)
            id_siniestro = fields.get("id_siniestro") or ids.get("id_siniestro")
            id_documento = fields.get("id_documento") or ids.get("id_documento")
            if not id_siniestro and not ids.get("id_documento") and not fields.get("id_documento"):
                stats["sin_relacion"] += 1
                details.append({
                    "archivo": target.name,
                    "rechazado": True,
                    "motivo": "No se detectó ID de siniestro SIN-xxxx ni ID de documento DOC-xxxx en el nombre o contenido del PDF.",
                })
                continue
            excel_doc = _find_excel_document(id_documento, id_siniestro, target.name)
            if excel_doc:
                id_documento = excel_doc.get("id_documento") or id_documento
                id_siniestro = excel_doc.get("id_siniestro") or id_siniestro
            if not id_documento:
                id_documento = f"AUTO-{target.stem[:40]}"
            listed = bool(excel_doc)
            if not listed:
                _upsert_document(id_documento, id_siniestro, doc_type, target.name, str(target), True)
                stats["sin_relacion"] += 1
            else:
                _upsert_document(id_documento, id_siniestro, doc_type, target.name, str(target), False)
                stats["vinculados"] += 1
            _insert_extracted(id_documento, id_siniestro, doc_type, target.name, target, method, text, fields, ocr_used, not listed)
            _insert_typed_document(id_documento, id_siniestro, doc_type, fields)
            stats["pdfs_procesados"] += 1
            stats["ocr_usado"] += 1 if ocr_used else 0
            details.append({"archivo": target.name, "id_siniestro": id_siniestro, "id_documento": id_documento, "tipo": doc_type, "metodo": method})
        except Exception as exc:
            stats["errores"] += 1
            details.append({"archivo": source_path.name, "error": str(exc)})
    _mark_missing_pdfs()
    analysis = recalculate_hackia_analysis()
    _log("pdf", "PDFs procesados", {"stats": stats, "detalles": details[:40], "analisis": analysis})
    return {"accepted": True, "stats": stats, "details": details, "analysis": analysis}


def recalculate_hackia_analysis() -> dict:
    ensure_hackia_schema()
    claims = _fetch_all("SELECT * FROM siniestros")
    policies = {row["id_poliza"]: row for row in _fetch_all("SELECT * FROM polizas")}
    insureds = {row["id_asegurado"]: row for row in _fetch_all("SELECT * FROM asegurados")}
    providers = {row["id_proveedor"]: row for row in _fetch_all("SELECT * FROM proveedores_hackia")}
    docs_by_claim = _group_by(_fetch_all("SELECT * FROM documentos"), "id_siniestro")
    invoices_by_claim = _group_by(_fetch_all("SELECT * FROM facturas"), "id_siniestro")
    police_by_claim = _group_by(_fetch_all("SELECT * FROM partes_policiales"), "id_siniestro")
    declarations_by_claim = _group_by(_fetch_all("SELECT * FROM declaraciones_accidente"), "id_siniestro")
    generated = 0
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM alertas_fraude")
            cursor.execute("DELETE FROM analisis_fraude")
            for claim in claims:
                alerts = _build_alerts_for_claim_cached(
                    claim,
                    policies.get(claim.get("id_poliza"), {}),
                    insureds.get(claim.get("id_asegurado"), {}),
                    providers.get(claim.get("id_proveedor"), {}),
                    docs_by_claim.get(claim["id_siniestro"], []),
                    invoices_by_claim.get(claim["id_siniestro"], []),
                    police_by_claim.get(claim["id_siniestro"], []),
                    declarations_by_claim.get(claim["id_siniestro"], []),
                )
                score = min(100, sum(_points(a["severidad"]) for a in alerts))
                score += min(12, int(_num(claim.get("reclamos_previos")) or 0) * 2)
                score += 8 if _risk_text(claim.get("similitud_narrativa_max")) else 0
                score = min(100, score)
                level = _risk_level(score)
                explanation = _score_explanation(score, level, alerts)
                if alerts:
                    cursor.executemany(
                        """
                        INSERT INTO alertas_fraude (
                          id_siniestro, tipo_alerta, severidad, explicacion, fuente_evidencia,
                          campo_detectado, valor_esperado, valor_encontrado
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        [
                            (
                                claim["id_siniestro"], a["tipo_alerta"], a["severidad"], a["explicacion"],
                                a["fuente_evidencia"], a["campo_detectado"], a.get("valor_esperado"), a.get("valor_encontrado"),
                            )
                            for a in alerts
                        ],
                    )
                cursor.execute(
                    """
                    INSERT INTO analisis_fraude (id_siniestro, puntaje_riesgo, nivel_riesgo, explicacion, factores)
                    VALUES (%s,%s,%s,%s,%s)
                    """,
                    (claim["id_siniestro"], score, level, explanation, json.dumps([a["tipo_alerta"] for a in alerts], ensure_ascii=False)),
                )
                generated += len(alerts)
        connection.commit()
    _log("analisis", "Análisis recalculado", {"siniestros": len(claims), "alertas": generated})
    return {"siniestros": len(claims), "alertas_generadas": generated}


def _group_by(rows: list[dict], key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row.get(key), []).append(row)
    return grouped


def hackia_summary() -> dict:
    ensure_hackia_schema()
    counts = {}
    for table in ["siniestros", "polizas", "asegurados", "proveedores_hackia", "documentos", "documentos_extraidos", "alertas_fraude"]:
        row = _fetch_one(f"SELECT COUNT(*) AS total FROM {table}")
        counts[table] = int(row["total"] if row else 0)
    risk = _fetch_all("SELECT nivel_riesgo, COUNT(*) AS total FROM analisis_fraude GROUP BY nivel_riesgo")
    logs = _fetch_all("SELECT tipo, mensaje, detalle, created_at FROM hackia_import_logs ORDER BY id DESC LIMIT 8")
    return {"counts": counts, "risk_distribution": risk, "logs": logs}


def hackia_executive_report() -> dict:
    ensure_hackia_schema()
    count_row = _fetch_one("SELECT COUNT(*) AS total, COALESCE(SUM(monto_reclamado), 0) AS amount FROM siniestros")
    total = int(count_row["total"] if count_row else 0)
    if total == 0:
        return {
            "summary": "Aun no hay siniestros importados. Sube un Excel desde Datos para generar el reporte ejecutivo.",
            "total_cases": 0,
            "critical_cases": 0,
            "main_signals": [],
            "providers": [],
            "cities": [],
            "recommendations": [],
            "limitations": [],
        }

    amount = float(count_row["amount"] or 0)
    risk_rows = _fetch_all("SELECT nivel_riesgo, COUNT(*) AS total FROM analisis_fraude GROUP BY nivel_riesgo")
    risk_counts = {row["nivel_riesgo"]: int(row["total"]) for row in risk_rows}
    high = risk_counts.get("Alto", 0) + risk_counts.get("Critico", 0)
    medium = risk_counts.get("Medio", 0)

    top_provider = _fetch_one(
        """
        SELECT COALESCE(p.nombre_proveedor, s.id_proveedor, 'Sin proveedor') AS provider_name,
               AVG(COALESCE(a.puntaje_riesgo, 0)) AS avg_score
        FROM siniestros s
        LEFT JOIN proveedores_hackia p ON p.id_proveedor=s.id_proveedor
        LEFT JOIN analisis_fraude a ON a.id_siniestro=s.id_siniestro
        GROUP BY provider_name
        ORDER BY avg_score DESC
        LIMIT 1
        """
    )
    provider_text = (
        f"{top_provider['provider_name']} (score promedio {float(top_provider['avg_score'] or 0):.1f})"
        if top_provider else "sin proveedor destacado"
    )
    signals = _fetch_all(
        """
        SELECT tipo_alerta AS signal_name, COUNT(*) AS alert_count
        FROM alertas_fraude
        GROUP BY tipo_alerta
        ORDER BY alert_count DESC, signal_name ASC
        LIMIT 8
        """
    )
    providers = _fetch_all(
        """
        SELECT COALESCE(p.nombre_proveedor, s.id_proveedor, 'Sin proveedor') AS provider_name,
               COUNT(af.id_alerta) AS alerts,
               ROUND(AVG(COALESCE(a.puntaje_riesgo, 0)), 1) AS avg_score
        FROM siniestros s
        LEFT JOIN proveedores_hackia p ON p.id_proveedor=s.id_proveedor
        LEFT JOIN analisis_fraude a ON a.id_siniestro=s.id_siniestro
        LEFT JOIN alertas_fraude af ON af.id_siniestro=s.id_siniestro
        GROUP BY provider_name
        HAVING alerts > 0
        ORDER BY alerts DESC, avg_score DESC
        LIMIT 5
        """
    )
    cities = _fetch_all(
        """
        SELECT COALESCE(ciudad, 'Sin ciudad') AS city,
               COUNT(*) AS claims,
               SUM(CASE WHEN a.nivel_riesgo IN ('Alto', 'Critico') THEN 1 ELSE 0 END) AS red_cases,
               ROUND(AVG(COALESCE(a.puntaje_riesgo, 0)), 1) AS avg_score
        FROM siniestros s
        LEFT JOIN analisis_fraude a ON a.id_siniestro=s.id_siniestro
        GROUP BY city
        ORDER BY red_cases DESC, avg_score DESC
        LIMIT 5
        """
    )
    return {
        "summary": (
            f"Se analizaron {total} siniestros importados por USD {amount:,.0f}. "
            f"Hay {high} casos de riesgo alto o critico y {medium} de riesgo medio. "
            f"Proveedor con mayor score promedio: {provider_text}."
        ),
        "total_cases": total,
        "critical_cases": high,
        "main_signals": [{"signal": row["signal_name"], "count": int(row["alert_count"])} for row in signals],
        "providers": [{"provider_name": row["provider_name"], "alerts": int(row["alerts"]), "avg_score": float(row["avg_score"] or 0)} for row in providers],
        "cities": [{"city": row["city"], "claims": int(row["claims"]), "red_cases": int(row["red_cases"] or 0), "avg_score": float(row["avg_score"] or 0)} for row in cities],
        "recommendations": [
            "Priorizar revision humana de casos con score superior a 75.",
            "Validar documentos faltantes, ilegibles o inconsistentes antes de cualquier decision.",
            "Revisar concentraciones por proveedor y ciudad como patrones operativos, no como acusaciones.",
        ],
        "limitations": [
            "El score es una alerta de revision, no una decision legal ni contractual.",
            "Requiere gobierno de datos, auditoria y validacion con expertos antes de uso productivo.",
        ],
    }


def hackia_model_status() -> dict:
    summary = hackia_summary()
    risk_counts = {item["nivel_riesgo"]: int(item["total"]) for item in summary.get("risk_distribution", [])}
    signals = _fetch_all(
        """
        SELECT tipo_alerta AS signal_name, COUNT(*) AS alert_count
        FROM alertas_fraude
        GROUP BY tipo_alerta
        ORDER BY alert_count DESC, signal_name ASC
        LIMIT 5
        """
    )
    top_cases = _fetch_all(
        """
        SELECT id_siniestro, puntaje_riesgo, nivel_riesgo
        FROM analisis_fraude
        ORDER BY puntaje_riesgo DESC, id_siniestro ASC
        LIMIT 5
        """
    )
    return {
        "approach": "Flujo HackIAthon: Excel + PDF/OCR + reglas explicables + agente IA sobre datos importados.",
        "layers": [
            {"name": "Validacion Excel", "weight": None, "implemented": True},
            {"name": "Extraccion PDF/OCR", "weight": None, "implemented": True},
            {"name": "Reglas explicables", "weight": None, "implemented": True},
            {"name": "Agente IA/Ollama", "weight": None, "implemented": True},
        ],
        "total_cases": int(summary.get("counts", {}).get("siniestros", 0)),
        "risk_distribution": {
            "critico": risk_counts.get("Critico", 0),
            "alto": risk_counts.get("Alto", 0),
            "medio": risk_counts.get("Medio", 0),
            "bajo": risk_counts.get("Bajo", 0),
        },
        "main_signals": [{"signal": row["signal_name"], "count": int(row["alert_count"])} for row in signals],
        "top_cases": [
            {
                "claim_id": row["id_siniestro"],
                "risk_score": int(row["puntaje_riesgo"]),
                "risk_level": row["nivel_riesgo"],
            }
            for row in top_cases
        ],
    }


def hackia_tables() -> dict:
    ensure_hackia_schema()
    return {
        "siniestros": _fetch_all("SELECT * FROM siniestros ORDER BY id_siniestro LIMIT 500"),
        "polizas": _fetch_all("SELECT * FROM polizas ORDER BY id_poliza LIMIT 500"),
        "asegurados": _fetch_all("SELECT * FROM asegurados ORDER BY id_asegurado LIMIT 500"),
        "proveedores": _fetch_all("SELECT * FROM proveedores_hackia ORDER BY id_proveedor LIMIT 500"),
        "documentos": _fetch_all("SELECT * FROM documentos ORDER BY id_siniestro, id_documento LIMIT 1000"),
        "analisis": _fetch_all("SELECT * FROM analisis_fraude ORDER BY puntaje_riesgo DESC LIMIT 500"),
    }


def hackia_uploaded_pdfs() -> list[dict]:
    ensure_hackia_schema()
    return _fetch_all(
        """
        SELECT d.id_documento, d.id_siniestro, d.tipo_documento, d.nombre_archivo_pdf, d.ruta_archivo,
               d.pdf_no_encontrado, d.documento_no_listado_en_excel,
               de.id AS extraccion_id, de.metodo_extraccion, de.ocr_usado, de.procesado_at,
               CHAR_LENGTH(COALESCE(de.texto_extraido, '')) AS caracteres_extraidos
        FROM documentos d
        LEFT JOIN (
          SELECT de1.*
          FROM documentos_extraidos de1
          INNER JOIN (
            SELECT id_documento, MAX(id) AS max_id
            FROM documentos_extraidos
            GROUP BY id_documento
          ) latest ON latest.max_id=de1.id
        ) de ON de.id_documento=d.id_documento
        WHERE d.ruta_archivo IS NOT NULL AND d.ruta_archivo <> ''
        ORDER BY d.id_siniestro, d.id_documento
        LIMIT 1000
        """
    )


def hackia_pdf_path(id_documento: str) -> Path | None:
    ensure_hackia_schema()
    row = _fetch_one(
        """
        SELECT ruta_archivo, nombre_archivo_pdf
        FROM documentos
        WHERE id_documento=%s AND ruta_archivo IS NOT NULL AND ruta_archivo <> ''
        """,
        (id_documento,),
    )
    if not row:
        return None
    path = Path(row["ruta_archivo"])
    return path if path.exists() and path.is_file() else None


def hackia_claims() -> list[dict]:
    ensure_hackia_schema()
    return _fetch_all(
        """
        SELECT s.id_siniestro, s.id_poliza, s.id_asegurado, s.ramo, s.placa, s.ciudad, s.id_proveedor,
               p.nombre_proveedor, s.fecha_siniestro, s.fecha_reporte, s.docs_completos,
               s.cobertura, s.estado, s.monto_reclamado, s.monto_estimado, s.monto_pagado,
               COALESCE(a.puntaje_riesgo, 0) AS puntaje_riesgo, COALESCE(a.nivel_riesgo, 'Bajo') AS nivel_riesgo,
               COUNT(DISTINCT d.id_documento) AS documentos,
               COUNT(DISTINCT de.id) AS pdfs_procesados,
               COUNT(DISTINCT af.id_alerta) AS alertas
        FROM siniestros s
        LEFT JOIN proveedores_hackia p ON p.id_proveedor=s.id_proveedor
        LEFT JOIN analisis_fraude a ON a.id_siniestro=s.id_siniestro
        LEFT JOIN documentos d ON d.id_siniestro=s.id_siniestro
        LEFT JOIN documentos_extraidos de ON de.id_siniestro=s.id_siniestro
        LEFT JOIN alertas_fraude af ON af.id_siniestro=s.id_siniestro
        GROUP BY s.id_siniestro, s.id_poliza, s.id_asegurado, s.ramo, s.placa, s.ciudad, s.id_proveedor,
                 p.nombre_proveedor, s.fecha_siniestro, s.fecha_reporte, s.docs_completos,
                 s.cobertura, s.estado, s.monto_reclamado, s.monto_estimado, s.monto_pagado,
                 a.puntaje_riesgo, a.nivel_riesgo
        ORDER BY puntaje_riesgo DESC, s.id_siniestro ASC
        LIMIT 1000
        """
    )


def hackia_claim_detail(id_siniestro: str) -> dict | None:
    ensure_hackia_schema()
    sid = normalize_sinister_id(id_siniestro)
    claim = _fetch_one("SELECT * FROM siniestros WHERE id_siniestro=%s", (sid,))
    if not claim:
        return None
    return {
        "siniestro": claim,
        "poliza": _fetch_one("SELECT * FROM polizas WHERE id_poliza=%s", (claim.get("id_poliza"),)),
        "asegurado": _fetch_one("SELECT * FROM asegurados WHERE id_asegurado=%s", (claim.get("id_asegurado"),)),
        "proveedor": _fetch_one("SELECT * FROM proveedores_hackia WHERE id_proveedor=%s", (claim.get("id_proveedor"),)),
        "documentos": _fetch_all("SELECT * FROM documentos WHERE id_siniestro=%s ORDER BY tipo_documento, id_documento", (sid,)),
        "extraidos": _fetch_all("SELECT * FROM documentos_extraidos WHERE id_siniestro=%s ORDER BY procesado_at DESC", (sid,)),
        "facturas": _fetch_all("SELECT * FROM facturas WHERE id_siniestro=%s", (sid,)),
        "partes_policiales": _fetch_all("SELECT * FROM partes_policiales WHERE id_siniestro=%s", (sid,)),
        "declaraciones": _fetch_all("SELECT * FROM declaraciones_accidente WHERE id_siniestro=%s", (sid,)),
        "alertas": _fetch_all("SELECT * FROM alertas_fraude WHERE id_siniestro=%s ORDER BY FIELD(severidad,'critica','alta','media','baja')", (sid,)),
        "analisis": _fetch_one("SELECT * FROM analisis_fraude WHERE id_siniestro=%s", (sid,)),
    }


def hackia_agent_context(question: str) -> str:
    ids = re.findall(r"SIN\s*[- ]?\s*\d{1,6}", question.upper())
    if ids:
        detail = hackia_claim_detail(ids[0])
        if not detail:
            return ""
        alerts = "; ".join([f"{a['tipo_alerta']} ({a['fuente_evidencia']})" for a in detail["alertas"][:8]])
        docs = "; ".join([f"{d['tipo_documento']} {d['id_documento']} pdf_no_encontrado={d['pdf_no_encontrado']}" for d in detail["documentos"][:10]])
        texts = " ".join([(e.get("texto_extraido") or "")[:700] for e in detail["extraidos"][:2]])
        invoices = "; ".join([f"factura {f.get('numero_factura')} RUC {f.get('ruc')} total {f.get('total_pagar')} caso {f.get('caso_marcado')} alterado={f.get('documento_alterado')}" for f in detail["facturas"][:4]])
        police = "; ".join([f"parte {p.get('numero_parte_policial')} placa {p.get('placa')} fecha {p.get('fecha')} tipo {p.get('tipo_accidente')} narrativa {(p.get('narrativa_accidente') or '')[:260]}" for p in detail["partes_policiales"][:3]])
        declarations = "; ".join([f"declaracion asegurado {d.get('asegurado')} placa {d.get('placa')} fecha {d.get('fecha_accidente')} descripcion {(d.get('descripcion_accidente') or '')[:260]}" for d in detail["declaraciones"][:3]])
        sid = detail["siniestro"]["id_siniestro"]
        return f"Contexto HackIAthon del siniestro {sid}: analisis={detail['analisis']}; documentos={docs}; facturas={invoices}; partes_policiales={police}; declaraciones={declarations}; alertas={alerts}; texto_pdf={texts}"
    top = hackia_claims()[:5]
    if not top:
        return ""
    return "Contexto HackIAthon top casos: " + "; ".join([f"{r['id_siniestro']} score {r['puntaje_riesgo']} {r['nivel_riesgo']} alertas {r['alertas']}" for r in top])


def _import_siniestros(frame: pd.DataFrame) -> int:
    rows = []
    for _, row in frame.iterrows():
        sid = normalize_sinister_id(_get(row, "id_siniestro", "id siniestro", "siniestro"))
        if not sid:
            continue
        rows.append((
            sid,
            normalize_generic_id(_get(row, "id_poliza", "id póliza", "id poliza"), "POL"),
            normalize_generic_id(_get(row, "id_asegurado", "id asegurado"), "ASE"),
            _date(_get(row, "fecha_siniestro", "fecha siniestro", "fecha_ocurrencia", "fecha ocurrencia")),
            _date(_get(row, "fecha_reporte", "fecha reporte")),
            _text(_get(row, "ramo")),
            normalize_plate(_get(row, "placa", "placa_vehiculo_asegurado", "placa vehículo asegurado", "placa vehiculo asegurado")),
            _text(_get(row, "cobertura")),
            _text(_get(row, "ciudad")),
            _text(_get(row, "sucursal")),
            normalize_generic_id(_get(row, "id_proveedor", "id proveedor"), "PROV"),
            _text(_get(row, "descripcion_evento", "descripción del evento", "descripcion del evento")),
            _bool(_get(row, "docs_completos", "docs completos", "documentos completos")),
            _bool(_get(row, "proveedor_lista_restrictiva", "proveedor en lista restrictiva", "prov_lista_restrictiva", "prov. lista restrictiva")),
            _int(_get(row, "dias_ocurr_reporte", "días ocurr→reporte", "dias ocurr reporte", "dias_ocurr_reporte", "días ocurrencia reporte")),
            _int(_get(row, "dias_desde_inicio_poliza", "días desde inicio póliza", "dias desde inicio poliza")),
            _int(_get(row, "dias_hasta_fin_poliza", "días hasta fin póliza", "dias hasta fin poliza")),
            _int(_get(row, "n_reclamos_previos", "n° reclamos previos", "reclamos previos", "n_reclamos_previos_asegurado", "n° reclamos previos asegurado")),
            _money(_get(row, "suma_asegurada", "suma asegurada", "suma_asegurada_$", "suma asegurada ($)")),
            _num(_get(row, "similitud_narrativa_max", "similitud narrativa máx", "similitud narrativa max", "similitud_narrativa_max")),
            _text(_get(row, "numero_parte_policial", "número parte policial", "numero parte policial")),
            _money(_get(row, "monto_reclamado", "monto reclamado", "monto_reclamado_$", "monto reclamado ($)")),
            _money(_get(row, "monto_estimado", "monto estimado", "monto_estimado_$", "monto estimado ($)")),
            _money(_get(row, "monto_pagado", "monto pagado", "monto_pagado_$", "monto pagado ($)")),
            _text(_get(row, "estado")),
        ))
    _executemany(
        """
        INSERT INTO siniestros (
          id_siniestro,id_poliza,id_asegurado,fecha_siniestro,fecha_reporte,ramo,placa,cobertura,ciudad,sucursal,
          id_proveedor,descripcion_evento,docs_completos,proveedor_lista_restrictiva,dias_ocurrencia_reporte,dias_desde_inicio_poliza,
          dias_hasta_fin_poliza,reclamos_previos,suma_asegurada,similitud_narrativa_max,numero_parte_policial,monto_reclamado,
          monto_estimado,monto_pagado,estado
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON DUPLICATE KEY UPDATE id_poliza=VALUES(id_poliza), id_asegurado=VALUES(id_asegurado),
          fecha_siniestro=VALUES(fecha_siniestro), fecha_reporte=VALUES(fecha_reporte), ramo=VALUES(ramo),
          placa=VALUES(placa), cobertura=VALUES(cobertura), ciudad=VALUES(ciudad), sucursal=VALUES(sucursal), id_proveedor=VALUES(id_proveedor),
          descripcion_evento=VALUES(descripcion_evento), docs_completos=VALUES(docs_completos),
          proveedor_lista_restrictiva=VALUES(proveedor_lista_restrictiva), dias_ocurrencia_reporte=VALUES(dias_ocurrencia_reporte),
          dias_desde_inicio_poliza=VALUES(dias_desde_inicio_poliza),
          dias_hasta_fin_poliza=VALUES(dias_hasta_fin_poliza), reclamos_previos=VALUES(reclamos_previos),
          suma_asegurada=VALUES(suma_asegurada), similitud_narrativa_max=VALUES(similitud_narrativa_max),
          numero_parte_policial=VALUES(numero_parte_policial), monto_reclamado=VALUES(monto_reclamado),
          monto_estimado=VALUES(monto_estimado), monto_pagado=VALUES(monto_pagado), estado=VALUES(estado)
        """,
        rows,
    )
    return len(rows)


def _import_polizas(frame: pd.DataFrame) -> int:
    rows = []
    for _, row in frame.iterrows():
        pid = normalize_generic_id(_get(row, "id_poliza", "id póliza", "id poliza"), "POL")
        if not pid:
            continue
        rows.append((pid, normalize_generic_id(_get(row, "id_asegurado", "id asegurado"), "ASE"), _text(_get(row, "ramo")), _date(_get(row, "fecha_inicio", "fecha inicio")), _date(_get(row, "fecha_fin", "fecha fin")), _money(_get(row, "suma_asegurada", "suma asegurada", "suma_asegurada_$", "suma asegurada ($)")), _money(_get(row, "prima_anual", "prima anual", "prima_anual_$", "prima anual ($)")), _text(_get(row, "canal_venta", "canal venta")), _text(_get(row, "estado_poliza", "estado póliza", "estado poliza"))))
    _executemany("INSERT INTO polizas VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE id_asegurado=VALUES(id_asegurado), ramo=VALUES(ramo), fecha_inicio=VALUES(fecha_inicio), fecha_fin=VALUES(fecha_fin), suma_asegurada=VALUES(suma_asegurada), prima_anual=VALUES(prima_anual), canal_venta=VALUES(canal_venta), estado_poliza=VALUES(estado_poliza)", rows)
    return len(rows)


def _import_asegurados(frame: pd.DataFrame) -> int:
    rows = []
    for _, row in frame.iterrows():
        aid = normalize_generic_id(_get(row, "id_asegurado", "id asegurado"), "ASE")
        if not aid:
            continue
        rows.append((aid, _text(_get(row, "nombres_asegurado", "nombres asegurado")), _text(_get(row, "segmento")), _text(_get(row, "ciudad")), _text(_get(row, "antiguedad", "antigüedad", "antiguedad_anos", "antigüedad (años)")), _int(_get(row, "n_polizas_activas", "n° pólizas activas", "polizas activas")), _int(_get(row, "n_reclamos_ultimos_12_meses", "n° reclamos últimos 12 meses")), _int(_get(row, "n_reclamos_historico_total", "n° reclamos histórico total")), _int(_get(row, "reclamos_rc_sin_tercero")), _text(_get(row, "perfil_riesgo_historico", "perfil riesgo histórico"))))
    _executemany("INSERT INTO asegurados VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE nombres_asegurado=VALUES(nombres_asegurado), segmento=VALUES(segmento), ciudad=VALUES(ciudad), antiguedad=VALUES(antiguedad), polizas_activas=VALUES(polizas_activas), reclamos_ultimos_12_meses=VALUES(reclamos_ultimos_12_meses), reclamos_historico_total=VALUES(reclamos_historico_total), reclamos_rc_sin_tercero=VALUES(reclamos_rc_sin_tercero), perfil_riesgo_historico=VALUES(perfil_riesgo_historico)", rows)
    return len(rows)


def _import_proveedores(frame: pd.DataFrame) -> int:
    rows = []
    for _, row in frame.iterrows():
        pid = normalize_generic_id(_get(row, "id_proveedor", "id proveedor"), "PROV")
        if not pid:
            continue
        promedio_raw = _get(row, "promedio_monto", "promedio monto ($)", "promedio monto", "promedio_monto_$")
        promedio = _money(promedio_raw)
        observation = None
        if promedio is None and promedio_raw not in (None, ""):
            observation = _text(promedio_raw)
            for value in row.values:
                candidate = _money(value)
                if candidate is not None:
                    promedio = candidate
        rows.append((pid, _text(_get(row, "nombre_proveedor", "nombre proveedor")), _text(_get(row, "tipo")), _text(_get(row, "ciudad")), _int(_get(row, "n_siniestros_asociados", "n° siniestros asociados")), _bool(_get(row, "en_lista_restrictiva", "en lista restrictiva")), _text(_get(row, "motivo_restriccion", "motivo restricción")), observation, promedio))
    _executemany("INSERT INTO proveedores_hackia VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE nombre_proveedor=VALUES(nombre_proveedor), tipo=VALUES(tipo), ciudad=VALUES(ciudad), siniestros_asociados=VALUES(siniestros_asociados), en_lista_restrictiva=VALUES(en_lista_restrictiva), motivo_restriccion=VALUES(motivo_restriccion), observacion_proveedor=VALUES(observacion_proveedor), promedio_monto=VALUES(promedio_monto)", rows)
    return len(rows)


def _import_documentos(documents: pd.DataFrame, index: pd.DataFrame) -> int:
    rows = []
    for frame in [documents, index]:
        if frame is None or frame.empty:
            continue
        for _, row in frame.iterrows():
            doc_id = normalize_document_id(_get(row, "id_documento", "id documento", "doc id", "doc id sistema"))
            file_name = _text(_get(row, "nombre_archivo_pdf", "nombre archivo pdf", "nombre de archivo", "archivo", "nombre archivo"))
            sid = normalize_sinister_id(_get(row, "id_siniestro", "id siniestro", "siniestro", "siniestro ref")) or _ids_from_filename(file_name or "").get("id_siniestro")
            if not doc_id and file_name:
                doc_id = _ids_from_filename(file_name).get("id_documento") or f"AUTO-{Path(file_name).stem[:40]}"
            if not doc_id:
                continue
            rows.append((doc_id, sid, _text(_get(row, "tipo_documento", "tipo de documento", "tipo documento")) or _detect_document_type(file_name or "", ""), file_name, False, False, None))
    _executemany(
        "INSERT INTO documentos (id_documento,id_siniestro,tipo_documento,nombre_archivo_pdf,pdf_no_encontrado,documento_no_listado_en_excel,ruta_archivo) VALUES (%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE id_siniestro=VALUES(id_siniestro), tipo_documento=VALUES(tipo_documento), nombre_archivo_pdf=VALUES(nombre_archivo_pdf), documento_no_listado_en_excel=FALSE",
        rows,
    )
    return len(rows)


def _build_alerts_for_claim(claim: dict) -> list[dict]:
    sid = claim["id_siniestro"]
    alerts = []
    pol = _fetch_one("SELECT * FROM polizas WHERE id_poliza=%s", (claim.get("id_poliza"),)) or {}
    insured = _fetch_one("SELECT * FROM asegurados WHERE id_asegurado=%s", (claim.get("id_asegurado"),)) or {}
    provider = _fetch_one("SELECT * FROM proveedores_hackia WHERE id_proveedor=%s", (claim.get("id_proveedor"),)) or {}
    docs = _fetch_all("SELECT * FROM documentos WHERE id_siniestro=%s", (sid,))
    facturas = _fetch_all("SELECT * FROM facturas WHERE id_siniestro=%s", (sid,))
    partes = _fetch_all("SELECT * FROM partes_policiales WHERE id_siniestro=%s", (sid,))
    declaraciones = _fetch_all("SELECT * FROM declaraciones_accidente WHERE id_siniestro=%s", (sid,))

    claim_date = claim.get("fecha_siniestro")
    if pol.get("fecha_fin") and claim_date and claim_date > pol["fecha_fin"]:
        alerts.append(_alert(sid, "Póliza expirada al momento del siniestro", "critica", "La fecha del siniestro ocurre después del fin de vigencia de la póliza.", "Excel", "fecha_siniestro", str(pol["fecha_fin"]), str(claim_date)))
    if _int(claim.get("dias_desde_inicio_poliza")) is not None and _int(claim.get("dias_desde_inicio_poliza")) <= 10:
        alerts.append(_alert(sid, "Siniestro cercano al inicio de póliza", "alta", "El evento ocurrió pocos días después del inicio de vigencia.", "Excel", "dias_desde_inicio_poliza", "> 10", claim.get("dias_desde_inicio_poliza")))
    if claim.get("fecha_siniestro") and claim.get("fecha_reporte") and (claim["fecha_reporte"] - claim["fecha_siniestro"]).days > 7:
        alerts.append(_alert(sid, "Reporte tardío", "media", "El siniestro fue reportado más de 7 días después del evento.", "Excel", "fecha_reporte", "≤ 7 días", str(claim["fecha_reporte"])))
    if _int(claim.get("dias_ocurrencia_reporte")) is not None and _int(claim.get("dias_ocurrencia_reporte")) > 7:
        alerts.append(_alert(sid, "Demora ocurrencia a reporte", "media", "La columna Días Ocurrencia-Reporte supera el umbral de revisión.", "Excel", "dias_ocurrencia_reporte", "≤ 7", claim.get("dias_ocurrencia_reporte")))
    if provider.get("en_lista_restrictiva") or claim.get("proveedor_lista_restrictiva"):
        alerts.append(_alert(sid, "Proveedor en lista restrictiva", "critica", f"Proveedor con restricción registrada: {provider.get('motivo_restriccion') or 'sin motivo detallado'}.", "Excel", "id_proveedor", "proveedor no restrictivo", claim.get("id_proveedor")))
    if _int(provider.get("siniestros_asociados")) and _int(provider.get("siniestros_asociados")) >= 10:
        alerts.append(_alert(sid, "Proveedor con alta concentración de siniestros", "alta", "El proveedor aparece asociado a una frecuencia elevada de casos.", "Excel", "siniestros_asociados", "< 10", provider.get("siniestros_asociados")))
    if claim.get("docs_completos") is False:
        alerts.append(_alert(sid, "Documentación incompleta", "alta", "El Excel indica que el expediente documental no está completo.", "Excel", "docs_completos", "Sí", "No"))
    estimated = _num(claim.get("monto_estimado"))
    claimed = _num(claim.get("monto_reclamado"))
    if estimated and claimed and claimed > estimated * 1.35:
        alerts.append(_alert(sid, "Monto reclamado superior al estimado", "media", "El monto reclamado supera en más de 35% al monto estimado.", "Excel", "monto_reclamado", f"≤ {estimated * 1.35:.2f}", f"{claimed:.2f}"))
    for doc in docs:
        if doc.get("pdf_no_encontrado"):
            alerts.append(_alert(sid, "PDF faltante", "media", "El documento figura en Excel pero no se encontró el PDF asociado.", "Excel/PDF", "nombre_archivo_pdf", doc.get("nombre_archivo_pdf"), "No encontrado"))
    if not any("parte" in (d.get("tipo_documento") or "").lower() for d in docs) and claim.get("numero_parte_policial"):
        alerts.append(_alert(sid, "Parte policial faltante", "alta", "Existe número de parte policial en Excel pero no se vinculó el PDF del parte.", "Excel/PDF", "numero_parte_policial", claim.get("numero_parte_policial"), "PDF no vinculado"))
    if partes and claim.get("numero_parte_policial"):
        for part in partes:
            if part.get("numero_parte_policial") and str(part["numero_parte_policial"]) != str(claim["numero_parte_policial"]):
                alerts.append(_alert(sid, "Número de parte policial inconsistente", "alta", "El número de parte del Excel no coincide con el extraído del PDF.", "Parte policial", "numero_parte_policial", claim["numero_parte_policial"], part["numero_parte_policial"]))
    for declaration in declaraciones:
        if declaration.get("placa") and claim.get("placa") and normalize_plate(declaration["placa"]) != normalize_plate(claim["placa"]):
            alerts.append(_alert(sid, "Placa inconsistente entre Excel y PDF", "critica", "La placa del Excel no coincide con la declaración de accidente.", "Declaración de accidente", "placa", claim["placa"], declaration["placa"]))
        if declaration.get("fecha_accidente") and claim_date and declaration["fecha_accidente"] != claim_date:
            alerts.append(_alert(sid, "Fecha de accidente inconsistente", "alta", "La fecha del accidente no coincide entre Excel y declaración.", "Declaración de accidente", "fecha_accidente", str(claim_date), str(declaration["fecha_accidente"])))
    for factura in facturas:
        if factura.get("documento_alterado"):
            alerts.append(_alert(sid, "Factura marcada como documento alterado", "critica", "El PDF contiene texto de documento alterado.", "Factura", "documento_alterado", "Legítimo", "DOCUMENTO ALTERADO"))
        if factura.get("ruc") and not _valid_ec_ruc(factura["ruc"]):
            alerts.append(_alert(sid, "Factura con RUC inválido", "alta", "El RUC extraído no cumple una validación básica de formato.", "Factura/OCR", "ruc", "13 dígitos válidos", factura["ruc"]))
        avg = _num(provider.get("promedio_monto"))
        total = _num(factura.get("total_pagar"))
        if avg and total and total > avg * 1.5:
            alerts.append(_alert(sid, "Factura superior al promedio del proveedor", "alta", "El total de la factura supera en más de 50% el promedio del proveedor.", "Factura + Excel", "total_pagar", f"≤ {avg * 1.5:.2f}", f"{total:.2f}"))
    if _int(insured.get("reclamos_historico_total")) and _int(insured.get("reclamos_historico_total")) >= 3:
        alerts.append(_alert(sid, "Asegurado con reclamos previos altos", "media", "El asegurado registra alta frecuencia histórica de reclamos.", "Excel", "reclamos_historico_total", "< 3", insured.get("reclamos_historico_total")))
    if str(insured.get("perfil_riesgo_historico") or "").lower() in {"alto", "critico", "crítico"}:
        alerts.append(_alert(sid, "Perfil histórico de riesgo alto", "alta", "El perfil histórico del asegurado está marcado como alto.", "Excel", "perfil_riesgo_historico", "Bajo/Medio", insured.get("perfil_riesgo_historico")))
    if _risk_text(claim.get("similitud_narrativa_max")):
        alerts.append(_alert(sid, "Narrativa similar a otros casos", "media", "La similitud narrativa máxima supera el umbral recomendado.", "Excel/NLP", "similitud_narrativa_max", "< 0.70", claim.get("similitud_narrativa_max")))
    return alerts


def _build_alerts_for_claim_cached(
    claim: dict,
    pol: dict,
    insured: dict,
    provider: dict,
    docs: list[dict],
    facturas: list[dict],
    partes: list[dict],
    declaraciones: list[dict],
) -> list[dict]:
    sid = claim["id_siniestro"]
    alerts = []
    claim_date = claim.get("fecha_siniestro")
    if pol.get("fecha_fin") and claim_date and claim_date > pol["fecha_fin"]:
        alerts.append(_alert(sid, "Póliza expirada al momento del siniestro", "critica", "La fecha del siniestro ocurre después del fin de vigencia de la póliza.", "Excel", "fecha_siniestro", str(pol["fecha_fin"]), str(claim_date)))
    if _int(claim.get("dias_desde_inicio_poliza")) is not None and _int(claim.get("dias_desde_inicio_poliza")) <= 10:
        alerts.append(_alert(sid, "Siniestro cercano al inicio de póliza", "alta", "El evento ocurrió pocos días después del inicio de vigencia.", "Excel", "dias_desde_inicio_poliza", "> 10", claim.get("dias_desde_inicio_poliza")))
    if claim.get("fecha_siniestro") and claim.get("fecha_reporte") and (claim["fecha_reporte"] - claim["fecha_siniestro"]).days > 7:
        alerts.append(_alert(sid, "Reporte tardío", "media", "El siniestro fue reportado más de 7 días después del evento.", "Excel", "fecha_reporte", "≤ 7 días", str(claim["fecha_reporte"])))
    if provider.get("en_lista_restrictiva") or claim.get("proveedor_lista_restrictiva"):
        alerts.append(_alert(sid, "Proveedor en lista restrictiva", "critica", f"Proveedor con restricción registrada: {provider.get('motivo_restriccion') or 'sin motivo detallado'}.", "Excel", "id_proveedor", "proveedor no restrictivo", claim.get("id_proveedor")))
    if _int(provider.get("siniestros_asociados")) and _int(provider.get("siniestros_asociados")) >= 10:
        alerts.append(_alert(sid, "Proveedor con alta concentración de siniestros", "alta", "El proveedor aparece asociado a una frecuencia elevada de casos.", "Excel", "siniestros_asociados", "< 10", provider.get("siniestros_asociados")))
    if claim.get("docs_completos") is False:
        alerts.append(_alert(sid, "Documentación incompleta", "alta", "El Excel indica que el expediente documental no está completo.", "Excel", "docs_completos", "Sí", "No"))
    for doc in docs:
        if doc.get("pdf_no_encontrado"):
            alerts.append(_alert(sid, "PDF faltante", "media", "El documento figura en Excel pero no se encontró el PDF asociado.", "Excel/PDF", "nombre_archivo_pdf", doc.get("nombre_archivo_pdf"), "No encontrado"))
    if not any("parte" in (d.get("tipo_documento") or "").lower() for d in docs) and claim.get("numero_parte_policial"):
        alerts.append(_alert(sid, "Parte policial faltante", "alta", "Existe número de parte policial en Excel pero no se vinculó el PDF del parte.", "Excel/PDF", "numero_parte_policial", claim.get("numero_parte_policial"), "PDF no vinculado"))
    if partes and claim.get("numero_parte_policial"):
        for part in partes:
            if part.get("numero_parte_policial") and str(part["numero_parte_policial"]) != str(claim["numero_parte_policial"]):
                alerts.append(_alert(sid, "Número de parte policial inconsistente", "alta", "El número de parte del Excel no coincide con el extraído del PDF.", "Parte policial", "numero_parte_policial", claim["numero_parte_policial"], part["numero_parte_policial"]))
    for declaration in declaraciones:
        if declaration.get("placa") and claim.get("placa") and normalize_plate(declaration["placa"]) != normalize_plate(claim["placa"]):
            alerts.append(_alert(sid, "Placa inconsistente entre Excel y PDF", "critica", "La placa del Excel no coincide con la declaración de accidente.", "Declaración de accidente", "placa", claim["placa"], declaration["placa"]))
        if declaration.get("fecha_accidente") and claim_date and declaration["fecha_accidente"] != claim_date:
            alerts.append(_alert(sid, "Fecha de accidente inconsistente", "alta", "La fecha del accidente no coincide entre Excel y declaración.", "Declaración de accidente", "fecha_accidente", str(claim_date), str(declaration["fecha_accidente"])))
    for factura in facturas:
        if factura.get("documento_alterado"):
            alerts.append(_alert(sid, "Factura marcada como documento alterado", "critica", "El PDF contiene texto de documento alterado.", "Factura", "documento_alterado", "Legítimo", "DOCUMENTO ALTERADO"))
        if factura.get("ruc") and not _valid_ec_ruc(factura["ruc"]):
            alerts.append(_alert(sid, "Factura con RUC inválido", "alta", "El RUC extraído no cumple una validación básica de formato.", "Factura/OCR", "ruc", "13 dígitos válidos", factura["ruc"]))
        avg = _num(provider.get("promedio_monto"))
        total = _num(factura.get("total_pagar"))
        if avg and total and total > avg * 1.5:
            alerts.append(_alert(sid, "Factura superior al promedio del proveedor", "alta", "El total de la factura supera en más de 50% el promedio del proveedor.", "Factura + Excel", "total_pagar", f"≤ {avg * 1.5:.2f}", f"{total:.2f}"))
    if _int(insured.get("reclamos_historico_total")) and _int(insured.get("reclamos_historico_total")) >= 3:
        alerts.append(_alert(sid, "Asegurado con reclamos previos altos", "media", "El asegurado registra alta frecuencia histórica de reclamos.", "Excel", "reclamos_historico_total", "< 3", insured.get("reclamos_historico_total")))
    if str(insured.get("perfil_riesgo_historico") or "").lower() in {"alto", "critico", "crítico"}:
        alerts.append(_alert(sid, "Perfil histórico de riesgo alto", "alta", "El perfil histórico del asegurado está marcado como alto.", "Excel", "perfil_riesgo_historico", "Bajo/Medio", insured.get("perfil_riesgo_historico")))
    if _risk_text(claim.get("similitud_narrativa_max")):
        alerts.append(_alert(sid, "Narrativa similar a otros casos", "media", "La similitud narrativa máxima supera el umbral recomendado.", "Excel/NLP", "similitud_narrativa_max", "< 0.70", claim.get("similitud_narrativa_max")))
    return alerts


def _extract_pdf_text(path: Path) -> tuple[str, str, bool]:
    text = ""
    try:
        reader = PdfReader(str(path))
        text = "\n".join([page.extract_text() or "" for page in reader.pages]).strip()
    except Exception:
        text = ""
    if len(text) >= 80:
        return text, "pdf_text", False
    try:
        from pdf2image import convert_from_path
        import pytesseract

        tesseract_path = find_tesseract_executable()
        poppler_bin = find_poppler_bin()
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = str(tesseract_path)
        if not tesseract_path:
            raise RuntimeError("Tesseract no encontrado")
        if not poppler_bin:
            raise RuntimeError("Poppler/pdftoppm no encontrado")

        images = convert_from_path(str(path), dpi=180, first_page=1, last_page=3, poppler_path=str(poppler_bin))
        text = "\n".join(pytesseract.image_to_string(image, lang="spa+eng") for image in images).strip()
        return text, "ocr", True
    except Exception as exc:
        return text or f"OCR no disponible o fallido: {exc}", "pdf_text_fallback", False


def find_tesseract_executable() -> Path | None:
    command = shutil.which("tesseract")
    if command:
        return Path(command)
    candidates = [
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files/Autopsy-4.22.1/autopsy/Tesseract-OCR/tesseract.exe"),
    ]
    return next((path for path in candidates if path.exists()), None)


def find_poppler_bin() -> Path | None:
    command = shutil.which("pdftoppm")
    if command:
        return Path(command).parent
    local_tools = Path("tools/poppler")
    if local_tools.exists():
        match = next(local_tools.rglob("pdftoppm.exe"), None)
        if match:
            return match.parent
    return None


def ocr_runtime_status() -> dict:
    tesseract = find_tesseract_executable()
    poppler = find_poppler_bin()
    return {
        "tesseract": {"ok": bool(tesseract), "path": str(tesseract) if tesseract else None},
        "poppler": {"ok": bool(poppler), "path": str(poppler) if poppler else None},
        "ready": bool(tesseract and poppler),
    }


def _extract_fields(text: str, doc_type: str, filename: str) -> dict:
    ids = _ids_from_filename(filename) | _ids_from_text(text)
    fields = dict(ids)
    fields.update(
        {
            "placa": normalize_plate(_match(text, r"\bPlaca[:\s]+([A-Z0-9-]{5,10})")),
            "fecha": _date(_match(text, r"\bFecha(?: del accidente)?[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})")),
            "lugar": _match(text, r"\bLugar[:\s]+(.{3,120})"),
            "asegurado": _match(text, r"\bAsegurado[:\s]+(.{3,120})"),
            "poliza": normalize_generic_id(_match(text, r"\bP[oó]liza[:\s]+([A-Z0-9-]+)"), "POL"),
            "ruc": _match(text, r"\bRUC[:\s]+(\d{10,13})"),
            "total_pagar": _money(_match(text, r"(?:Total a pagar|Total)[:\s$]+([\d.,]+)")),
            "numero_factura": _match(text, r"(?:Factura|Nro\.?|Número)[:\s#-]+([A-Z0-9-]+)"),
            "numero_parte_policial": _match(text, r"(?:Parte Policial|N[úu]mero de parte|Parte No\.?)[:\s#-]+([A-Z0-9-]+)"),
            "documento_alterado": "DOCUMENTO ALTERADO" in text.upper(),
            "caso_marcado": _match(text, r"\bCaso[:\s]+(Fraude|Leg[ií]timo)"),
            "descripcion": _match(text, r"(?:Descripci[oó]n(?: del accidente)?|Narrativa)[:\s]+(.{20,900})"),
        }
    )
    if doc_type == "Factura":
        fields["subtotal"] = _money(_match(text, r"Subtotal[:\s$]+([\d.,]+)"))
        fields["iva"] = _money(_match(text, r"IVA[:\s$]+([\d.,]+)"))
        fields["cliente"] = _match(text, r"Cliente[:\s]+(.{3,120})")
        fields["taller_proveedor"] = _match(text, r"(?:Taller|Proveedor)[:\s]+(.{3,120})")
    return {key: value for key, value in fields.items() if value not in (None, "")}


def normalize_sinister_id(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.search(r"SIN\s*[-\s]?\s*(\d{1,6})", text.upper())
    return f"SIN-{int(match.group(1)):04d}" if match else None


def normalize_document_id(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    match = re.search(r"DOC[-\s]?(\d{1,6})", text.upper())
    return f"DOC-{int(match.group(1)):04d}" if match else None


def normalize_generic_id(value: Any, prefix: str) -> str | None:
    text = _text(value)
    if not text:
        return None
    return text.upper().replace(" ", "-")


def normalize_plate(value: Any) -> str | None:
    text = _text(value)
    return re.sub(r"[^A-Z0-9]", "", text.upper()) if text else None


def _canonical_sheet(name: str) -> str:
    return _slug(name).replace("_", "")


def _clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.dropna(how="all").copy()
    frame.columns = [_slug(str(column)) if str(column).strip() and not str(column).startswith("Unnamed") else f"unnamed_{index}" for index, column in enumerate(frame.columns)]
    return frame


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", normalized).strip("_").lower()
    return normalized


def _get(row: pd.Series, *names: str) -> Any:
    lookup = {_slug(name) for name in names}
    for key, value in row.items():
        if key in lookup:
            return value
    return None


def _text(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return None if text.lower() in {"nan", "none", "--", ""} else re.sub(r"\s+", " ", text)


def _bool(value: Any) -> bool | None:
    text = (_text(value) or "").lower()
    if text in {"si", "sí", "s", "true", "1", "x", "yes"}:
        return True
    if text in {"no", "false", "0", "n"}:
        return False
    return None


def _date(value: Any) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=True)
    return None if pd.isna(parsed) else parsed.date()


def _money(value: Any) -> float | None:
    text = _text(value)
    if not text:
        return None
    cleaned = re.sub(r"[^0-9,.-]", "", text)
    if cleaned.count(",") == 1 and cleaned.count(".") >= 1:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif cleaned.count(",") == 1 and cleaned.count(".") == 0:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    return _money(value)


def _int(value: Any) -> int | None:
    number = _num(value)
    return None if number is None else int(number)


def _ids_from_filename(filename: str) -> dict:
    return {"id_siniestro": normalize_sinister_id(filename), "id_documento": normalize_document_id(filename)}


def _ids_from_text(text: str) -> dict:
    return {"id_siniestro": normalize_sinister_id(text), "id_documento": normalize_document_id(text)}


def _merge_detected_ids(*sources: dict) -> dict:
    merged = {"id_siniestro": None, "id_documento": None}
    for source in sources:
        for key in merged:
            if source.get(key):
                merged[key] = source[key]
    return merged


def _detect_document_type(filename: str, text: str) -> str:
    source = f"{filename} {text[:500]}".upper()
    if "FACTURA" in source:
        return "Factura"
    if re.search(r"\bDA[_-]|DECLARACION|DECLARACIÓN", source):
        return "Declaración de accidente"
    if re.search(r"\bPP[_-]|PARTE POLICIAL", source):
        return "Parte policial"
    return "Otro documento"


def _match(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return _text(match.group(1).split("\n")[0])


def _match_any(text: str, patterns: list[str]) -> str | None:
    for pattern in patterns:
        value = _match(text, pattern)
        if value:
            return value
    return None


def _match_block(text: str, start_pattern: str, stop_patterns: list[str]) -> str | None:
    start = re.search(start_pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not start:
        return None
    fragment = text[start.end():]
    stop_index = len(fragment)
    for pattern in stop_patterns:
        stop = re.search(pattern, fragment, flags=re.IGNORECASE | re.DOTALL)
        if stop:
            stop_index = min(stop_index, stop.start())
    return _text(fragment[:stop_index])


def _extract_fields(text: str, doc_type: str, filename: str) -> dict:
    ids = _merge_detected_ids(_ids_from_filename(filename), _ids_from_text(text))
    fields = dict(ids)
    fields.update({
        "placa": normalize_plate(_match_any(text, [r"\bPlaca[:\s]+([A-Z0-9-]{5,10})", r"\bPlaca[:\s]*\n(?:.*\n){0,8}?([A-Z]{2,4}-?\d{3,4})"])),
        "fecha": _date(_match_any(text, [r"\bFecha(?: del accidente)?[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})", r"\bFecha\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"])),
        "lugar": _match_any(text, [r"\bLugar[:\s]+(.{3,120})", r"\bLugar\s+(.{3,160}?)(?:\s+Velocidad|\n)"]),
        "asegurado": _match_any(text, [r"\bAsegurado[:\s]+(.{3,120})", r"\bAsegurado\s+(.{3,140}?)(?:\s+Correo|\s+Direcci[oó]n|\n)"]),
        "poliza": normalize_generic_id(_match_any(text, [r"\bP[oó]liza[:\s]+([A-Z0-9-]+)", r"\bP[oó]liza\s+([A-Z0-9-]{5,60})"]), "POL"),
        "ruc": _match(text, r"\bRUC[:\s]+(\d{10,13})"),
        "total_pagar": _money(_match_any(text, [r"TOTAL A PAGAR[\s\S]{0,500}?\$?\s*([\d.,]+)\s*(?:Caso|Este|$)", r"(?:Total a pagar|Total)[:\s$]+([\d.,]+)"])),
        "numero_factura": _match_any(text, [r"FACTURA\s*N[º°o.]?\s*[:#-]?\s*([A-Z0-9-]+)", r"(?:Factura|Nro\.?|Numero|Número)[:\s#-]+([A-Z0-9-]+)"]),
        "numero_parte_policial": _match_any(text, [r"Parte Policial No[:.\s]+([A-Z0-9-]+)", r"Parte No[:.\s]+([A-Z0-9-]+)", r"(?:Parte Policial|Numero de parte|Número de parte)[:\s#-]+([A-Z0-9-]+)"]),
        "documento_alterado": "DOCUMENTO ALTERADO" in text.upper(),
        "caso_marcado": _match_any(text, [r"\bCaso[:\s]+(Fraude|Leg[ií]timo|Legitimo)"]),
        "descripcion": _match_block(text, r"(?:Descripci[oó]n(?: del accidente)?|Narrativa|Explique detalladamente c[oó]mo ocurri[oó] el accidente)[:\s]+", [r"A juicio del conductor", r"DATOS SOBRE EL CONTRARIO", r"INTERVENCI[OÓ]N", r"Parte Elevado", r"PARTICIPANTE", r"\n\s*Documento sint[eé]tico"]),
    })
    if doc_type == "Factura":
        fields.update(_extract_invoice_fields(text))
    elif doc_type == "Parte policial":
        fields.update(_extract_police_fields(text))
    elif "Declaraci" in doc_type:
        fields.update(_extract_declaration_fields(text))
    return {key: value for key, value in fields.items() if value not in (None, "")}


def _extract_invoice_fields(text: str) -> dict:
    placa = _match_any(text, [r"Placa:\s*\n(?:.*\n){0,8}?([A-Z]{2,4}-?\d{3,4})", r"\bPlaca[:\s]+([A-Z0-9-]{5,10})"])
    total = _money(_match_any(text, [r"TOTAL A PAGAR[\s\S]{0,500}?\$?\s*([\d.,]+)\s*(?:Caso|Este|$)"]))
    values = {
        "numero_factura": _match_any(text, [r"N[º°o.]?\s*:\s*([0-9]{3}-[0-9]{3}-[0-9]+)", r"FACTURA[\s\S]{0,80}?([0-9]{3}-[0-9]{3}-[0-9]+)"]),
        "subtotal": _money(_match_any(text, [r"Subtotal(?:\s+\d+%)?\s*\$?\s*([\d.,]+)"])),
        "iva": _money(_match_any(text, [r"IVA(?:\s+\d+%)?\s*\$?\s*([\d.,]+)"])),
        "cliente": _match_any(text, [r"Cliente:\s*\n(?:.*\n){0,4}?([A-ZÁÉÍÓÚÑa-záéíóúñ][^\n]{3,120})", r"Cliente[:\s]+(.{3,120})"]),
        "taller_proveedor": _match_any(text, [r"^([A-ZÁÉÍÓÚÑ0-9 .,&-]{5,160})\s*\nServicios", r"(?:Taller|Proveedor)[:\s]+(.{3,120})"]),
        "vehiculo": _match_any(text, [r"Veh[ií]culo:\s*\n?([^\n]{3,120})"]),
        "fecha": _date(_match_any(text, [r"\bFecha:\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"])),
        "caso_marcado": _match_any(text, [r"\bCaso:\s*(Fraude|Leg[ií]timo|Legitimo|Leg.timo)"]),
        "descripcion": _match_block(text, r"Descripci[oó]n\s*", [r"V\. Unitario", r"TOTAL A PAGAR", r"Subtotal"]),
    }
    if placa:
        values["placa"] = normalize_plate(placa)
    if total is not None:
        values["total_pagar"] = total
    return values


def _extract_police_fields(text: str) -> dict:
    calle_1 = _match_any(text, [r"Calle 1:\s*(.{3,160})"])
    calle_2 = _match_any(text, [r"Calle 2:\s*(.{3,160})"])
    lugar = " / ".join([part for part in [calle_1, calle_2] if part]) or _match(text, r"\bLugar[:\s]+(.{3,120})")
    return {
        "numero_parte_policial": _match_any(text, [r"Parte Policial No[:.\s]+([A-Z0-9-]+)", r"Parte No[:.\s]+([A-Z0-9-]+)"]),
        "fecha": _date(_match_any(text, [r"Fecha del Hecho:\s*(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", r"Fecha de Elaboracion:\s*(\d{4}-\d{2}-\d{2})"])),
        "hora": _match_any(text, [r"Hora Aproximada:\s*([0-9:]{4,8})", r"Hora:\s*([0-9:]{4,8})"]),
        "lugar": lugar,
        "placa": normalize_plate(_match_any(text, [r"Vehiculo Placa\s+([A-Z0-9-]{5,10})", r"Placa:\s*([A-Z0-9-]{5,10})"])),
        "marca": _match_any(text, [r"Marca:\s*([A-Z0-9ÁÉÍÓÚÑ -]{2,60})"]),
        "modelo": _match_any(text, [r"Modelo:\s*([A-Z0-9ÁÉÍÓÚÑ -]{2,80})"]),
        "motor": _match_any(text, [r"Motor:\s*([A-Z0-9-]{4,80})"]),
        "chasis": _match_any(text, [r"Chasis:\s*([A-Z0-9-]{8,120})"]),
        "tipo_accidente": _match_any(text, [r"\[X\]\s*([A-ZÁÉÍÓÚÑa-záéíóúñ ]{3,40})"]),
        "consecuencias": _match_any(text, [r"Consecuencias:\s*(.{3,120})"]),
        "clima": _match_any(text, [r"Clima:\s*(.{2,60})"]),
        "autoridad_agente": _match_any(text, [r"Parte Elevado al Sr/a:\s*(.{3,120})"]),
        "descripcion": _match_block(text, r"Circunstancias del Hecho:\s*", [r"Parte Elevado", r"PARTICIPANTE", r"Personal Policial"]),
        "observaciones": _match_any(text, [r"OBSERVACION:\s*(.{5,220})", r"Observaciones:\s*(.{5,220})"]),
    }


def _extract_declaration_fields(text: str) -> dict:
    return {
        "asegurado": _match_any(text, [r"Asegurado\s+(.{3,140}?)(?:\s+Correo|\s+Direcci[oó]n|\n)", r"Asegurado[:\s]+(.{3,120})"]),
        "telefono": _match_any(text, [r"Tel[eé]fono\s+([0-9 +()-]{7,30})"]),
        "direccion": _match_any(text, [r"Direcci[oó]n\s+(.{3,180}?)(?:\s+Tel[eé]fono|\s+P[oó]liza|\n)"]),
        "poliza": _match_any(text, [r"P[oó]liza\s+([A-Z0-9-]{5,60})"]),
        "marca": _match_any(text, [r"Marca\s+([A-Z0-9ÁÉÍÓÚÑ -]{2,60})(?:\s+Modelo|\n)"]),
        "modelo": _match_any(text, [r"Modelo\s+([A-Z0-9ÁÉÍÓÚÑ -]{2,80})(?:\s+Tipo|\n)"]),
        "color": _match_any(text, [r"Color\s+([A-ZÁÉÍÓÚÑa-záéíóúñ ]{3,40})(?:\s+Placa|\n)"]),
        "placa": normalize_plate(_match_any(text, [r"Placa\s+([A-Z0-9-]{5,10})"])),
        "motor": _match_any(text, [r"Motor\s+([A-Z0-9-]{4,80})"]),
        "chasis": _match_any(text, [r"Chasis\s+([A-Z0-9-]{8,120})"]),
        "fecha": _date(_match_any(text, [r"Fecha\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})"])),
        "hora": _match_any(text, [r"Hora\s+([0-9:]{4,8})"]),
        "lugar": _match_any(text, [r"Lugar\s+(.{3,160}?)(?:\s+Velocidad|\n)"]),
        "velocidad": _match_any(text, [r"Velocidad\s+([0-9]+\s*Km/h|[0-9]+)"]),
        "descripcion": _match_block(text, r"Explique detalladamente.*?accidente[:\s]+", [r"A juicio del conductor", r"DATOS SOBRE EL CONTRARIO", r"INTERVENCI[OÓ]N"]),
        "responsable_conductor": _match_block(text, r"A juicio del conductor.*?\n", [r"Nombres y apellidos", r"DATOS SOBRE EL CONTRARIO"]),
        "datos_contrario": _match_block(text, r"DATOS SOBRE EL CONTRARIO[\s\S]{0,80}", [r"INTERVENCI[OÓ]N DE AUTORIDADES"]),
        "intervencion_autoridades": _match_any(text, [r"agentes tomaron nota del parte\?\s*(.{3,120})"]),
        "lugar_asistencia_medica": _match_block(text, r"Lugar donde se recibe asistencia m[eé]dica\s*", [r"El que suscribe", r"Nota:", r"DOCUMENTO SINT"]),
    }


def _upsert_document(doc_id: str, sid: str | None, doc_type: str, filename: str, path: str, not_listed: bool) -> None:
    _execute(
        """
        INSERT INTO documentos (id_documento,id_siniestro,tipo_documento,nombre_archivo_pdf,pdf_no_encontrado,documento_no_listado_en_excel,ruta_archivo)
        VALUES (%s,%s,%s,%s,FALSE,%s,%s)
        ON DUPLICATE KEY UPDATE id_siniestro=COALESCE(VALUES(id_siniestro),id_siniestro), tipo_documento=VALUES(tipo_documento),
          nombre_archivo_pdf=VALUES(nombre_archivo_pdf), pdf_no_encontrado=FALSE,
          documento_no_listado_en_excel=VALUES(documento_no_listado_en_excel), ruta_archivo=VALUES(ruta_archivo)
        """,
        (doc_id, sid, doc_type, filename, not_listed, path),
    )


def _insert_extracted(doc_id: str, sid: str | None, doc_type: str, filename: str, path: Path, method: str, text: str, fields: dict, ocr_used: bool, not_listed: bool) -> None:
    _execute(
        """
        INSERT INTO documentos_extraidos (
          id_documento,id_siniestro,tipo_documento,nombre_archivo,ruta_archivo,metodo_extraccion,texto_extraido,
          campos_extraidos,ocr_usado,documento_no_listado_en_excel,pdf_no_encontrado
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,FALSE)
        ON DUPLICATE KEY UPDATE id_documento=VALUES(id_documento), id_siniestro=VALUES(id_siniestro),
          tipo_documento=VALUES(tipo_documento), ruta_archivo=VALUES(ruta_archivo), metodo_extraccion=VALUES(metodo_extraccion),
          texto_extraido=VALUES(texto_extraido), campos_extraidos=VALUES(campos_extraidos), ocr_usado=VALUES(ocr_usado),
          documento_no_listado_en_excel=VALUES(documento_no_listado_en_excel)
        """,
        (doc_id, sid, doc_type, filename, str(path), method, text, json.dumps(fields, ensure_ascii=False, default=str), ocr_used, not_listed),
    )


def _insert_typed_document(doc_id: str, sid: str | None, doc_type: str, fields: dict) -> None:
    if doc_type == "Factura":
        _execute("DELETE FROM facturas WHERE id_documento=%s", (doc_id,))
        _execute("INSERT INTO facturas (id_documento,id_siniestro,numero_factura,fecha,taller_proveedor,ruc,cliente,placa,vehiculo,subtotal,iva,total_pagar,descripciones_reparacion,documento_alterado,caso_marcado) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", (doc_id, sid, fields.get("numero_factura"), _date(fields.get("fecha")), fields.get("taller_proveedor"), fields.get("ruc"), fields.get("cliente"), fields.get("placa"), fields.get("vehiculo"), fields.get("subtotal"), fields.get("iva"), fields.get("total_pagar"), fields.get("descripcion"), bool(fields.get("documento_alterado")), fields.get("caso_marcado")))
    elif doc_type == "Parte policial":
        _execute("DELETE FROM partes_policiales WHERE id_documento=%s", (doc_id,))
        _execute("INSERT INTO partes_policiales (id_documento,id_siniestro,numero_parte_policial,fecha,lugar,narrativa_accidente,observaciones_relevantes) VALUES (%s,%s,%s,%s,%s,%s,%s)", (doc_id, sid, fields.get("numero_parte_policial"), _date(fields.get("fecha")), fields.get("lugar"), fields.get("descripcion"), fields.get("observaciones")))
    elif doc_type == "Declaración de accidente":
        _execute("DELETE FROM declaraciones_accidente WHERE id_documento=%s", (doc_id,))
        _execute("INSERT INTO declaraciones_accidente (id_documento,id_siniestro,asegurado,poliza,placa,fecha_accidente,lugar,descripcion_accidente) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (doc_id, sid, fields.get("asegurado"), fields.get("poliza"), fields.get("placa"), _date(fields.get("fecha")), fields.get("lugar"), fields.get("descripcion")))


def _insert_typed_document(doc_id: str, sid: str | None, doc_type: str, fields: dict) -> None:
    if doc_type == "Factura":
        _execute("DELETE FROM facturas WHERE id_documento=%s", (doc_id,))
        _execute(
            """
            INSERT INTO facturas (
              id_documento,id_siniestro,numero_factura,fecha,taller_proveedor,ruc,cliente,placa,vehiculo,
              subtotal,iva,total_pagar,descripciones_reparacion,documento_alterado,caso_marcado
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                doc_id, sid, fields.get("numero_factura"), _date(fields.get("fecha")), fields.get("taller_proveedor"),
                fields.get("ruc"), fields.get("cliente"), fields.get("placa"), fields.get("vehiculo"),
                fields.get("subtotal"), fields.get("iva"), fields.get("total_pagar"), fields.get("descripcion"),
                bool(fields.get("documento_alterado")), fields.get("caso_marcado"),
            ),
        )
    elif doc_type == "Parte policial":
        _execute("DELETE FROM partes_policiales WHERE id_documento=%s", (doc_id,))
        _execute(
            """
            INSERT INTO partes_policiales (
              id_documento,id_siniestro,numero_parte_policial,fecha,lugar,vehiculos_involucrados,
              narrativa_accidente,autoridad_agente,observaciones_relevantes,hora,placa,marca,modelo,motor,chasis,
              tipo_accidente,consecuencias,clima
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                doc_id, sid, fields.get("numero_parte_policial"), _date(fields.get("fecha")), fields.get("lugar"),
                fields.get("vehiculos_involucrados"), fields.get("descripcion"), fields.get("autoridad_agente"),
                fields.get("observaciones"), fields.get("hora"), fields.get("placa"), fields.get("marca"),
                fields.get("modelo"), fields.get("motor"), fields.get("chasis"), fields.get("tipo_accidente"),
                fields.get("consecuencias"), fields.get("clima"),
            ),
        )
    elif "Declaraci" in doc_type:
        _execute("DELETE FROM declaraciones_accidente WHERE id_documento=%s", (doc_id,))
        _execute(
            """
            INSERT INTO declaraciones_accidente (
              id_documento,id_siniestro,asegurado,telefono,direccion,poliza,placa,marca,modelo,color,chasis,
              motor,fecha_accidente,hora,lugar,velocidad,descripcion_accidente,responsable_conductor,
              datos_contrario,intervencion_autoridades,lugar_asistencia_medica
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                doc_id, sid, fields.get("asegurado"), fields.get("telefono"), fields.get("direccion"),
                fields.get("poliza"), fields.get("placa"), fields.get("marca"), fields.get("modelo"),
                fields.get("color"), fields.get("chasis"), fields.get("motor"), _date(fields.get("fecha")),
                fields.get("hora"), fields.get("lugar"), fields.get("velocidad"), fields.get("descripcion"),
                fields.get("responsable_conductor"), fields.get("datos_contrario"), fields.get("intervencion_autoridades"),
                fields.get("lugar_asistencia_medica"),
            ),
        )


def _find_excel_document(doc_id: str | None, sid: str | None, filename: str) -> dict | None:
    if doc_id:
        row = _fetch_one("SELECT * FROM documentos WHERE id_documento=%s", (doc_id,))
        if row:
            return row
    row = _fetch_one("SELECT * FROM documentos WHERE nombre_archivo_pdf=%s", (filename,))
    if row:
        return row
    if sid:
        stem = Path(filename).stem.lower()
        candidates = _fetch_all("SELECT * FROM documentos WHERE id_siniestro=%s", (sid,))
        for candidate in candidates:
            expected = (candidate.get("nombre_archivo_pdf") or "").lower()
            if expected and (expected == filename.lower() or Path(expected).stem.lower() == stem):
                return candidate
        doc_type = _detect_document_type(filename, "")
        for candidate in candidates:
            if doc_type.lower() in (candidate.get("tipo_documento") or "").lower() or (candidate.get("tipo_documento") or "").lower() in doc_type.lower():
                return candidate
    return None


def _validate_pdf_against_excel(doc_id: str | None, sid: str | None, filename: str, doc_type: str) -> tuple[dict | None, str | None]:
    if doc_id:
        row = _fetch_one("SELECT * FROM documentos WHERE id_documento=%s", (doc_id,))
        if not row:
            return None, f"El documento {doc_id} no existe en la hoja 5_Documentos del Excel cargado."
        expected_sid = row.get("id_siniestro")
        if sid and expected_sid and normalize_sinister_id(sid) != normalize_sinister_id(expected_sid):
            return None, f"El documento {doc_id} pertenece a {expected_sid}, pero el PDF indica {sid}."
        return row, None

    row = _fetch_one("SELECT * FROM documentos WHERE nombre_archivo_pdf=%s", (filename,))
    if row:
        expected_sid = row.get("id_siniestro")
        if sid and expected_sid and normalize_sinister_id(sid) != normalize_sinister_id(expected_sid):
            return None, f"El archivo {filename} esta listado para {expected_sid}, pero el PDF indica {sid}."
        return row, None

    if not sid:
        return None, "No se pudo vincular el PDF contra un siniestro/documento del Excel cargado."

    claim = _fetch_one("SELECT id_siniestro FROM siniestros WHERE id_siniestro=%s", (sid,))
    if not claim:
        return None, f"El siniestro {sid} no existe en la hoja 1_Siniestros del Excel cargado."

    stem = Path(filename).stem.lower()
    candidates = _fetch_all("SELECT * FROM documentos WHERE id_siniestro=%s", (sid,))
    for candidate in candidates:
        expected = (candidate.get("nombre_archivo_pdf") or "").lower()
        if expected and (expected == filename.lower() or Path(expected).stem.lower() == stem):
            return candidate, None

    for candidate in candidates:
        expected_type = (candidate.get("tipo_documento") or "").lower()
        incoming_type = doc_type.lower()
        if expected_type and (incoming_type in expected_type or expected_type in incoming_type):
            return candidate, None

    return None, f"El PDF indica {sid}, pero no coincide con ningun documento esperado en la hoja 5_Documentos."


def _reject_pdf(stats: dict, details: list[dict], filename: str, reason: str | None, sid: str | None = None, doc_id: str | None = None, doc_type: str | None = None) -> None:
    stats["rechazados"] += 1
    stats["sin_relacion"] += 1
    detail = {"archivo": filename, "rechazado": True, "motivo": reason or "PDF no reconocido como documento valido del dataset cargado."}
    if sid:
        detail["id_siniestro"] = sid
    if doc_id:
        detail["id_documento"] = doc_id
    if doc_type:
        detail["tipo"] = doc_type
    details.append(detail)


def _mark_missing_pdfs() -> None:
    _execute("UPDATE documentos SET pdf_no_encontrado=TRUE WHERE ruta_archivo IS NULL OR ruta_archivo=''")


def _valid_ec_ruc(value: str) -> bool:
    digits = re.sub(r"\D", "", value or "")
    return len(digits) == 13 and not digits.startswith("000")


def _risk_text(value: Any) -> bool:
    number = _num(value)
    return number is not None and number >= 0.70


def _points(severity: str) -> int:
    return {"baja": 5, "media": 10, "alta": 18, "critica": 28}.get(severity, 5)


def _risk_level(score: int) -> str:
    if score <= 30:
        return "Bajo"
    if score <= 60:
        return "Medio"
    if score <= 80:
        return "Alto"
    return "Critico"


def _score_explanation(score: int, level: str, alerts: list[dict]) -> str:
    top = ", ".join([a["tipo_alerta"] for a in alerts[:4]]) or "sin alertas relevantes"
    return f"Score {score}/100 ({level}). Factores principales: {top}. Esta alerta requiere revisión humana y no constituye acusación de fraude."


def _alert(sid: str, tipo: str, severity: str, explanation: str, source: str, field: str, expected: Any, found: Any) -> dict:
    return {"id_siniestro": sid, "tipo_alerta": tipo, "severidad": severity, "explicacion": explanation, "fuente_evidencia": source, "campo_detectado": field, "valor_esperado": None if expected is None else str(expected), "valor_encontrado": None if found is None else str(found)}


def _fetch_one(query: str, params: tuple = ()) -> dict | None:
    rows = _fetch_all(query, params)
    return rows[0] if rows else None


def _fetch_all(query: str, params: tuple = ()) -> list[dict]:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()


def _execute(query: str, params: tuple = ()) -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
        connection.commit()


def _executemany(query: str, rows: list[tuple]) -> None:
    if not rows:
        return
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.executemany(query, rows)
        connection.commit()


def _log(kind: str, message: str, detail: dict) -> None:
    try:
        _execute("INSERT INTO hackia_import_logs (tipo,mensaje,detalle) VALUES (%s,%s,%s)", (kind, message, json.dumps(detail, ensure_ascii=False, default=str)))
    except Exception:
        pass
