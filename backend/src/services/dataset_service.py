from __future__ import annotations

import random
from datetime import timedelta
from pathlib import Path

import pandas as pd

from backend.src.ingestion.load_data import DATA_DIR
from backend.src.services.database_service import (
    existing_ids,
    has_source_data,
    insert_claims_with_documents,
    load_source_tables,
)


DOC_TYPES = ["formulario de reclamo", "cedula", "fotos del siniestro", "factura/proforma", "informe tecnico"]
REQUIRED_COLUMNS = {
    "claim_id", "policy_id", "customer_id", "anonymous_customer", "provider_id",
    "line", "coverage", "city", "claim_date", "report_date", "claim_amount", "narrative",
}
ALLOWED_LINES = {"Vehiculos", "Salud", "Hogar", "Vida", "Empresarial"}
NARRATIVES = [
    "Accidente con tercero identificado y soporte fotografico completo.",
    "Reporte de robo en parqueadero residencial durante la noche.",
    "Evento ocurrido en zona aislada durante la madrugada, sin testigos identificados.",
    "Accidente sin tercero identificado, no hubo testigos y el reporte se realizo dias despues.",
    "Danos por agua reportados luego de lluvias intensas con fotografias de soporte.",
    "Atencion medica por emergencia con facturas y epicrisis adjuntas.",
]


def _next_claim_id(claims: pd.DataFrame, offset: int) -> str:
    max_id = claims["claim_id"].astype(str).str.replace("CLM-", "", regex=False).astype(int).max() if not claims.empty else 0
    return f"CLM-{max_id + offset:04d}"


def generate_additional_claims(count: int = 25, risk_mix: str = "balanceado") -> dict:
    count = max(1, min(int(count), 100))
    random.seed()
    if not has_source_data():
        raise RuntimeError("La base checkia no tiene datos. Sincroniza la semilla SQL antes de generar CSV.")

    data = load_source_tables()
    policies = data["policies"]
    customers = data["customers"]
    providers = data["providers"]
    claims = data["claims"]

    generated = []
    for index in range(1, count + 1):
        policy = policies.sample(1).iloc[0]
        customer = customers[customers["customer_id"] == policy["customer_id"]].iloc[0]
        provider = providers.sample(1).iloc[0]
        start = pd.to_datetime(policy["policy_start_date"]).date()
        end = pd.to_datetime(policy["policy_end_date"]).date()
        high_bias = risk_mix == "alto" or (risk_mix == "balanceado" and random.random() < 0.35)

        if high_bias:
            claim_date = random.choice([
                start + timedelta(days=random.randint(2, 25)),
                end - timedelta(days=random.randint(1, 18)),
                start + timedelta(days=random.randint(45, 330)),
            ])
            report_delay = random.randint(8, 21)
            amount_ratio = random.uniform(0.62, 0.96)
            narrative = random.choice(NARRATIVES[2:4])
        else:
            claim_date = start + timedelta(days=random.randint(35, 310))
            report_delay = random.randint(0, 6)
            amount_ratio = random.uniform(0.05, 0.45)
            narrative = random.choice(NARRATIVES)

        claim_date = min(max(claim_date, start), end - timedelta(days=1))
        generated.append(
            {
                "claim_id": _next_claim_id(claims, index),
                "policy_id": policy["policy_id"],
                "customer_id": customer["customer_id"],
                "anonymous_customer": customer["anonymous_customer"],
                "vehicle_id": f"VEH-{random.randint(1, 95):03d}" if policy["line"] == "Vehiculos" else "",
                "provider_id": provider["provider_id"],
                "line": policy["line"],
                "coverage": random.choice(["Choque parcial", "Perdida total por robo", "Gastos medicos", "Robo domiciliario", "Danos a maquinaria"]),
                "city": customer["city"],
                "claim_date": claim_date.isoformat(),
                "report_date": (claim_date + timedelta(days=report_delay)).isoformat(),
                "claim_amount": round(float(policy["insured_amount"]) * amount_ratio, 2),
                "narrative": narrative,
                "recent_customer_change": bool(high_bias and random.random() < 0.35),
            }
        )

    new_claims = pd.DataFrame(generated)
    generated_dir = DATA_DIR / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    export_path = generated_dir / f"generated_claims_{len(claims) + 1}_{len(claims) + count}.csv"
    new_claims.to_csv(export_path, index=False, sep=";", encoding="utf-8-sig")
    return {
        "created": len(new_claims),
        "csv_file": export_path.name,
        "download_url": f"/api/dataset/download/{export_path.name}",
        "message": "CSV generado para descarga. No modifica MySQL hasta que lo cargues manualmente.",
    }


def _read_uploaded_csv(file_path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(file_path, sep=None, engine="python", encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(file_path, sep=None, engine="python", encoding="latin-1")


def append_uploaded_claims(file_path: Path) -> dict:
    incoming = _read_uploaded_csv(file_path)
    incoming.columns = [str(column).strip().replace("\ufeff", "") for column in incoming.columns]
    received_rows = int(len(incoming))
    missing = sorted(REQUIRED_COLUMNS - set(incoming.columns))
    if missing:
        return {
            "accepted": False,
            "reason": "El archivo no parece corresponder a siniestros de CheckIA.",
            "missing_columns": missing,
            "required_columns": sorted(REQUIRED_COLUMNS),
            "detected_columns": list(incoming.columns),
        }

    validation_errors = _validate_claim_rows(incoming)
    if validation_errors:
        return {
            "accepted": False,
            "reason": "El archivo tiene columnas correctas, pero algunos valores no son validos para el modelo.",
            "validation_errors": validation_errors,
            "required_columns": sorted(REQUIRED_COLUMNS),
            "detected_columns": list(incoming.columns),
        }

    db_claim_ids = existing_ids("claims", "claim_id")
    incoming["claim_id"] = incoming["claim_id"].astype(str).str.strip()
    duplicate_mask = incoming["claim_id"].isin(db_claim_ids) | incoming["claim_id"].duplicated(keep="first")
    skipped_duplicates = int(duplicate_mask.sum())
    duplicate_claim_ids = incoming.loc[duplicate_mask, "claim_id"].head(10).tolist()
    incoming = incoming[~duplicate_mask].copy()
    if incoming.empty:
        return {
            "accepted": True,
            "inserted": 0,
            "received_rows": received_rows,
            "skipped_duplicates": skipped_duplicates,
            "duplicate_claim_ids": duplicate_claim_ids,
            "total_claims": len(db_claim_ids),
            "message": "El CSV fue valido, pero no contiene siniestros nuevos para agregar a MySQL.",
        }

    if "vehicle_id" not in incoming.columns:
        incoming["vehicle_id"] = ""
    if "recent_customer_change" not in incoming.columns:
        incoming["recent_customer_change"] = False

    reference_errors = _validate_foreign_keys(incoming)
    if reference_errors:
        return {
            "accepted": False,
            "reason": "El archivo contiene IDs que no existen en la base de datos.",
            "validation_errors": reference_errors,
            "required_columns": sorted(REQUIRED_COLUMNS),
            "detected_columns": list(incoming.columns),
        }

    columns = [
        "claim_id", "policy_id", "customer_id", "anonymous_customer", "vehicle_id", "provider_id",
        "line", "coverage", "city", "claim_date", "report_date", "claim_amount", "narrative", "recent_customer_change",
    ]
    incoming = incoming[columns]
    new_docs = [
        {"claim_id": row.claim_id, "document_type": doc_type, "status": "completo"}
        for row in incoming.itertuples()
        for doc_type in DOC_TYPES
    ]
    inserted = insert_claims_with_documents(incoming, new_docs)

    from backend.src.services.claims_service import get_claims_dataset, sync_database

    get_claims_dataset.cache_clear()
    sync_database()
    total_claims = int(len(get_claims_dataset()))
    return {
        "accepted": True,
        "inserted": inserted["inserted"],
        "received_rows": received_rows,
        "skipped_duplicates": skipped_duplicates,
        "duplicate_claim_ids": duplicate_claim_ids,
        "total_claims": total_claims,
        "message": "Carga incremental completada en MySQL. Los resultados IA fueron recalculados y sincronizados.",
    }


def _validate_foreign_keys(frame: pd.DataFrame) -> list[str]:
    errors = []
    policies = existing_ids("policies", "policy_id")
    customers = existing_ids("customers", "customer_id")
    providers = existing_ids("providers", "provider_id")
    missing_policies = sorted(set(frame["policy_id"].astype(str)) - policies)
    missing_customers = sorted(set(frame["customer_id"].astype(str)) - customers)
    missing_providers = sorted(set(frame["provider_id"].astype(str)) - providers)
    if missing_policies:
        errors.append(f"policy_id no existe en la base: {', '.join(missing_policies[:10])}.")
    if missing_customers:
        errors.append(f"customer_id no existe en la base: {', '.join(missing_customers[:10])}.")
    if missing_providers:
        errors.append(f"provider_id no existe en la base: {', '.join(missing_providers[:10])}.")
    return errors


def _validate_claim_rows(frame: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    if frame.empty:
        return ["El archivo no contiene filas de siniestros."]

    sample = frame.head(50).copy()
    if not sample["claim_id"].astype(str).str.match(r"^CLM-\d{4,}$").all():
        errors.append("La columna claim_id debe usar formato CLM-0001.")
    if not sample["policy_id"].astype(str).str.match(r"^POL-\d{4,}$").all():
        errors.append("La columna policy_id debe usar formato POL-0001.")
    if not sample["customer_id"].astype(str).str.match(r"^CUST-\d{3,}$").all():
        errors.append("La columna customer_id debe usar formato CUST-001.")
    if not sample["provider_id"].astype(str).str.match(r"^PRV-\d{3,}$").all():
        errors.append("La columna provider_id debe usar formato PRV-001.")

    parsed_claim_dates = pd.to_datetime(sample["claim_date"], errors="coerce")
    parsed_report_dates = pd.to_datetime(sample["report_date"], errors="coerce")
    if parsed_claim_dates.isna().any() or parsed_report_dates.isna().any():
        errors.append("Las columnas claim_date y report_date deben tener fechas validas, por ejemplo 2026-03-15.")
    elif (parsed_report_dates < parsed_claim_dates).any():
        errors.append("report_date no puede ser anterior a claim_date.")

    amounts = pd.to_numeric(sample["claim_amount"], errors="coerce")
    if amounts.isna().any() or (amounts <= 0).any():
        errors.append("claim_amount debe ser numerico y mayor que cero.")

    invalid_lines = sorted(set(sample["line"].dropna().astype(str)) - ALLOWED_LINES)
    if invalid_lines:
        errors.append(f"line contiene ramos no reconocidos: {', '.join(invalid_lines)}.")

    if sample["narrative"].fillna("").astype(str).str.len().lt(12).any():
        errors.append("narrative debe contener una descripcion del reclamo con suficiente contexto.")

    return errors
