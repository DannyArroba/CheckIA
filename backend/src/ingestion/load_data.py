from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


def _read_csv(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"No se encontro el archivo de datos: {path}")
    return pd.read_csv(path)


def load_claims() -> pd.DataFrame:
    return _read_csv("synthetic_claims.csv")


def load_policies() -> pd.DataFrame:
    return _read_csv("synthetic_policies.csv")


def load_customers() -> pd.DataFrame:
    return _read_csv("synthetic_customers.csv")


def load_providers() -> pd.DataFrame:
    return _read_csv("synthetic_providers.csv")


def load_documents() -> pd.DataFrame:
    return _read_csv("synthetic_documents.csv")


def load_all_data() -> dict[str, pd.DataFrame]:
    return {
        "claims": load_claims(),
        "policies": load_policies(),
        "customers": load_customers(),
        "providers": load_providers(),
        "documents": load_documents(),
    }
