# Modelo de Datos

## synthetic_claims.csv

Contiene los siniestros sintéticos:

- `claim_id`
- `policy_id`
- `customer_id`
- `anonymous_customer`
- `vehicle_id`
- `provider_id`
- `line`
- `coverage`
- `city`
- `claim_date`
- `report_date`
- `claim_amount`
- `narrative`
- `recent_customer_change`

## synthetic_policies.csv

Contiene vigencia y suma asegurada:

- `policy_id`
- `customer_id`
- `line`
- `policy_start_date`
- `policy_end_date`
- `insured_amount`
- `premium_status`

## synthetic_customers.csv

Clientes anonimizados:

- `customer_id`
- `anonymous_customer`
- `city`
- `age_range`
- `segment`
- `recent_customer_change`

## synthetic_providers.csv

Proveedores simulados:

- `provider_id`
- `provider_name`
- `provider_type`
- `provider_city`
- `restricted_simulated`

## synthetic_documents.csv

Documentos por siniestro:

- `claim_id`
- `document_type`
- `status`

Estados posibles: completo, faltante, ilegible e inconsistente.

## Base SQL

El esquema relacional está en `database/checkia.sql` y crea la base `checkia`.

Tablas principales:

- `customers`
- `policies`
- `providers`
- `claims`
- `claim_documents`
- `claim_risk_results`
- `claim_rule_results`
- `agent_messages`

Vistas:

- `vw_dashboard_summary`
- `vw_provider_alerts`
- `vw_city_alerts`
