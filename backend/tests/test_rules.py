from backend.src.rules.fraud_rules import evaluate_claim_rules, score_rules


def test_policy_start_and_documents_rules_activate():
    claim = {
        "claim_date": "2026-02-10",
        "report_date": "2026-02-20",
        "claim_amount": 9000,
        "coverage": "Perdida total por robo",
        "narrative": "Robo en zona aislada sin testigos durante la madrugada.",
        "recent_customer_change": True,
    }
    context = {
        "policy": {"policy_start_date": "2026-02-01", "policy_end_date": "2027-02-01", "insured_amount": 10000},
        "provider": {"restricted_simulated": True},
        "documents": {"missing_count": 1, "has_illegible": False, "has_inconsistent": True},
        "customer_claim_count": 3,
        "vehicle_claim_count": 1,
        "provider_claim_count": 8,
        "max_provider_claim_count": 20,
        "similar_narrative_score": 0.9,
    }
    rules = evaluate_claim_rules(claim, context)
    codes = {rule["codigo"] for rule in rules}

    assert "POLICY_START_PROXIMITY" in codes
    assert "INCOMPLETE_DOCUMENTS" in codes
    assert "SIMULATED_RESTRICTED_PROVIDER" in codes
    assert score_rules(rules) <= 100
