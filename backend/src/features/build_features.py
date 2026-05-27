from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.src.rules.fraud_rules import evaluate_claim_rules, score_rules


def add_similarity_scores(claims: pd.DataFrame) -> pd.DataFrame:
    result = claims.copy()
    narratives = result["narrative"].fillna("")
    if len(result) <= 1:
        result["similar_narrative_score"] = 0.0
        result["similar_claim_id"] = ""
        return result

    vectorizer = TfidfVectorizer(stop_words=None, ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform(narratives)
    similarities = cosine_similarity(matrix)
    np.fill_diagonal(similarities, 0)
    best_idx = similarities.argmax(axis=1)
    result["similar_narrative_score"] = similarities.max(axis=1).round(4)
    result["similar_claim_id"] = [result.iloc[idx]["claim_id"] for idx in best_idx]
    return result


def build_claim_contexts(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    claims = add_similarity_scores(data["claims"])
    policies = data["policies"]
    providers = data["providers"]
    documents = data["documents"]

    customer_counts = claims.groupby("customer_id")["claim_id"].count().to_dict()
    vehicle_counts = claims.groupby("vehicle_id")["claim_id"].count().to_dict()
    provider_counts = claims.groupby("provider_id")["claim_id"].count().to_dict()
    max_provider_count = max(provider_counts.values()) if provider_counts else 1

    document_summary = documents.groupby("claim_id").agg(
        missing_count=("status", lambda values: int((values == "faltante").sum())),
        has_illegible=("status", lambda values: bool((values == "ilegible").any())),
        has_inconsistent=("status", lambda values: bool((values == "inconsistente").any())),
        document_statuses=("status", lambda values: ", ".join(sorted(set(values)))),
        document_names=("document_type", lambda values: ", ".join(values)),
    ).reset_index()

    policy_details = policies.drop(columns=["customer_id", "line"], errors="ignore")
    enriched = claims.merge(policy_details, on="policy_id", how="left")
    enriched = enriched.merge(providers, on="provider_id", how="left")
    enriched = enriched.merge(document_summary, on="claim_id", how="left")
    enriched["missing_count"] = enriched["missing_count"].fillna(0).astype(int)
    enriched["has_illegible"] = enriched["has_illegible"].fillna(False).astype(bool)
    enriched["has_inconsistent"] = enriched["has_inconsistent"].fillna(False).astype(bool)
    enriched["document_statuses"] = enriched["document_statuses"].fillna("sin registros")
    enriched["document_names"] = enriched["document_names"].fillna("")

    rules_list = []
    rule_scores = []
    for _, row in enriched.iterrows():
        claim = row.to_dict()
        context = {
            "policy": row.to_dict(),
            "provider": row.to_dict(),
            "documents": row.to_dict(),
            "customer_claim_count": customer_counts.get(row["customer_id"], 0),
            "vehicle_claim_count": vehicle_counts.get(row["vehicle_id"], 0),
            "provider_claim_count": provider_counts.get(row["provider_id"], 0),
            "max_provider_claim_count": max_provider_count,
            "similar_narrative_score": row["similar_narrative_score"],
        }
        active_rules = evaluate_claim_rules(claim, context)
        rules_list.append(active_rules)
        rule_scores.append(score_rules(active_rules))

    enriched["rules"] = rules_list
    enriched["rule_score"] = rule_scores
    return enriched


def build_model_features(enriched: pd.DataFrame) -> pd.DataFrame:
    features = pd.DataFrame()
    features["claim_amount"] = enriched["claim_amount"].astype(float)
    features["amount_ratio"] = enriched["claim_amount"].astype(float) / enriched["insured_amount"].astype(float).clip(lower=1)
    features["days_to_report"] = (
        pd.to_datetime(enriched["report_date"]) - pd.to_datetime(enriched["claim_date"])
    ).dt.days.clip(lower=0)
    features["days_from_policy_start"] = (
        pd.to_datetime(enriched["claim_date"]) - pd.to_datetime(enriched["policy_start_date"])
    ).dt.days.clip(lower=0)
    features["days_to_policy_end"] = (
        pd.to_datetime(enriched["policy_end_date"]) - pd.to_datetime(enriched["claim_date"])
    ).dt.days.clip(lower=0)
    features["missing_count"] = enriched["missing_count"].astype(int)
    features["has_illegible"] = enriched["has_illegible"].astype(int)
    features["has_inconsistent"] = enriched["has_inconsistent"].astype(int)
    features["similar_narrative_score"] = enriched["similar_narrative_score"].astype(float)
    features["recent_customer_change"] = enriched["recent_customer_change"].astype(int)
    return features.fillna(0)
