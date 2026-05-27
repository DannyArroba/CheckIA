from __future__ import annotations

import random
from datetime import timedelta
from pathlib import Path

import pandas as pd

from backend.src.ingestion.load_data import DATA_DIR
from backend.src.services.claims_service import get_claims_dataset


DOC_TYPES = ["formulario de reclamo", "cedula", "fotos del siniestro", "factura/proforma", "informe tecnico"]
NARRATIVES = [
    "Accidente con tercero identificado y soporte fotografico completo.",
    "Reporte de robo en parqueadero residencial durante la noche.",
    "Evento ocurrido en zona aislada durante la madrugada, sin testigos identificados.",
    "Accidente sin tercero identificado, no hubo testigos y el reporte se realizo dias despues.",
    "Danos por agua reportados luego de lluvias intensas con fotografias de soporte.",
    "Atencion medica por emergencia con facturas y epicrisis adjuntas.",
]


def _next_claim_id(claims: pd.DataFrame, offset: int) -> str:
    max_id = claims["claim_id"].str.replace("CLM-", "", regex=False).astype(int).max()
    return f"CLM-{max_id + offset:04d}"


def generate_additional_claims(count: int = 25, risk_mix: str = "balanceado") -> dict:
    count = max(1, min(int(count), 100))
    random.seed()

    claims_path = DATA_DIR / "synthetic_claims.csv"
    policies = pd.read_csv(DATA_DIR / "synthetic_policies.csv")
    customers = pd.read_csv(DATA_DIR / "synthetic_customers.csv")
    providers = pd.read_csv(DATA_DIR / "synthetic_providers.csv")
    claims = pd.read_csv(claims_path)

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
        claim_id = _next_claim_id(claims, index)
        generated.append(
            {
                "claim_id": claim_id,
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
        "message": "CSV generado para descarga. No se agregó al dataset activo hasta que lo cargues manualmente.",
    }


def _read_uploaded_csv(file_path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(file_path, sep=None, engine="python", encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(file_path, sep=None, engine="python", encoding="latin-1")


def append_uploaded_claims(file_path: Path) -> dict:
    incoming = _read_uploaded_csv(file_path)
    incoming.columns = [str(column).strip().replace("\ufeff", "") for column in incoming.columns]
    required = {
        "claim_id", "policy_id", "customer_id", "anonymous_customer", "provider_id",
        "line", "coverage", "city", "claim_date", "report_date", "claim_amount", "narrative",
    }
    missing = sorted(required - set(incoming.columns))
    if missing:
        return {"accepted": False, "missing_columns": missing}

    claims_path = DATA_DIR / "synthetic_claims.csv"
    existing = pd.read_csv(claims_path)
    incoming = incoming[~incoming["claim_id"].isin(existing["claim_id"])]
    if incoming.empty:
        return {"accepted": True, "inserted": 0, "message": "El CSV no contiene siniestros nuevos."}

    if "vehicle_id" not in incoming.columns:
        incoming["vehicle_id"] = ""
    if "recent_customer_change" not in incoming.columns:
        incoming["recent_customer_change"] = False

    incoming = incoming[existing.columns]
    pd.concat([existing, incoming], ignore_index=True).to_csv(claims_path, index=False)

    docs_path = DATA_DIR / "synthetic_documents.csv"
    documents = pd.read_csv(docs_path)
    new_docs = [
        {"claim_id": row.claim_id, "document_type": doc_type, "status": "completo"}
        for row in incoming.itertuples()
        for doc_type in DOC_TYPES
    ]
    pd.concat([documents, pd.DataFrame(new_docs)], ignore_index=True).to_csv(docs_path, index=False)
    get_claims_dataset.cache_clear()

    return {"accepted": True, "inserted": int(len(incoming)), "total_claims": int(len(get_claims_dataset()))}
