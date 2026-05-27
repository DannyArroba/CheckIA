-- CheckIA - Base de datos local para demo
-- Motor recomendado: MySQL 8+ o MariaDB 10.6+

CREATE DATABASE IF NOT EXISTS checkia
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE checkia;

CREATE TABLE IF NOT EXISTS customers (
  customer_id VARCHAR(20) PRIMARY KEY,
  anonymous_customer VARCHAR(80) NOT NULL,
  city VARCHAR(80) NOT NULL,
  age_range VARCHAR(20) NOT NULL,
  segment VARCHAR(40) NOT NULL,
  recent_customer_change BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS policies (
  policy_id VARCHAR(20) PRIMARY KEY,
  customer_id VARCHAR(20) NOT NULL,
  line VARCHAR(60) NOT NULL,
  policy_start_date DATE NOT NULL,
  policy_end_date DATE NOT NULL,
  insured_amount DECIMAL(14,2) NOT NULL,
  premium_status VARCHAR(40) NOT NULL,
  CONSTRAINT fk_policies_customer
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS providers (
  provider_id VARCHAR(20) PRIMARY KEY,
  provider_name VARCHAR(120) NOT NULL,
  provider_type VARCHAR(60) NOT NULL,
  provider_city VARCHAR(80) NOT NULL,
  restricted_simulated BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS claims (
  claim_id VARCHAR(20) PRIMARY KEY,
  policy_id VARCHAR(20) NOT NULL,
  customer_id VARCHAR(20) NOT NULL,
  anonymous_customer VARCHAR(80) NOT NULL,
  vehicle_id VARCHAR(20),
  provider_id VARCHAR(20) NOT NULL,
  line VARCHAR(60) NOT NULL,
  coverage VARCHAR(120) NOT NULL,
  city VARCHAR(80) NOT NULL,
  claim_date DATE NOT NULL,
  report_date DATE NOT NULL,
  claim_amount DECIMAL(14,2) NOT NULL,
  narrative TEXT NOT NULL,
  recent_customer_change BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_claims_policy
    FOREIGN KEY (policy_id) REFERENCES policies(policy_id),
  CONSTRAINT fk_claims_customer
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
  CONSTRAINT fk_claims_provider
    FOREIGN KEY (provider_id) REFERENCES providers(provider_id)
);

CREATE TABLE IF NOT EXISTS claim_documents (
  document_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  claim_id VARCHAR(20) NOT NULL,
  document_type VARCHAR(100) NOT NULL,
  status ENUM('completo', 'faltante', 'ilegible', 'inconsistente') NOT NULL DEFAULT 'completo',
  CONSTRAINT fk_documents_claim
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
);

CREATE TABLE IF NOT EXISTS claim_risk_results (
  claim_id VARCHAR(20) PRIMARY KEY,
  rule_score DECIMAL(6,2) NOT NULL,
  model_score DECIMAL(6,2) NOT NULL,
  nlp_score DECIMAL(6,2) NOT NULL,
  risk_score INT NOT NULL,
  risk_level ENUM('Bajo', 'Medio', 'Alto') NOT NULL,
  risk_color ENUM('Verde', 'Amarillo', 'Rojo') NOT NULL,
  recommended_action VARCHAR(160) NOT NULL,
  explanation TEXT NOT NULL,
  calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_risk_claim
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
);

CREATE TABLE IF NOT EXISTS claim_rule_results (
  rule_result_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  claim_id VARCHAR(20) NOT NULL,
  rule_code VARCHAR(80) NOT NULL,
  rule_name VARCHAR(160) NOT NULL,
  points INT NOT NULL,
  severity ENUM('baja', 'media', 'alta') NOT NULL,
  explanation TEXT NOT NULL,
  CONSTRAINT fk_rule_claim
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
);

CREATE TABLE IF NOT EXISTS agent_conversations (
  conversation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(160) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_messages (
  message_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  conversation_id BIGINT,
  role ENUM('usuario', 'agente') NOT NULL,
  message_text TEXT NOT NULL,
  provider VARCHAR(40) NOT NULL DEFAULT 'ollama',
  sort_order INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_messages_conversation
    FOREIGN KEY (conversation_id) REFERENCES agent_conversations(conversation_id)
);

CREATE TABLE IF NOT EXISTS claim_review_actions (
  review_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  claim_id VARCHAR(20) NOT NULL,
  status ENUM('pendiente', 'bajo_observacion', 'documentacion_solicitada', 'revisado_sin_alerta', 'derivado_analista') NOT NULL,
  note TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_review_claim
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id)
);

CREATE INDEX idx_claims_dates ON claims(claim_date, report_date);
CREATE INDEX idx_claims_city ON claims(city);
CREATE INDEX idx_claims_provider ON claims(provider_id);
CREATE INDEX idx_claims_line ON claims(line);
CREATE INDEX idx_documents_status ON claim_documents(status);
CREATE INDEX idx_risk_level_score ON claim_risk_results(risk_level, risk_score);
CREATE INDEX idx_rules_claim_code ON claim_rule_results(claim_id, rule_code);
CREATE INDEX idx_agent_conversations_updated ON agent_conversations(updated_at);
CREATE INDEX idx_agent_messages_order ON agent_messages(sort_order, message_id);
CREATE INDEX idx_review_claim ON claim_review_actions(claim_id, created_at);

CREATE OR REPLACE VIEW vw_dashboard_summary AS
SELECT
  COUNT(*) AS total_claims,
  SUM(CASE WHEN r.risk_level = 'Bajo' THEN 1 ELSE 0 END) AS green_cases,
  SUM(CASE WHEN r.risk_level = 'Medio' THEN 1 ELSE 0 END) AS yellow_cases,
  SUM(CASE WHEN r.risk_level = 'Alto' THEN 1 ELSE 0 END) AS red_cases,
  SUM(c.claim_amount) AS total_claim_amount,
  COUNT(DISTINCT CASE WHEN r.risk_level IN ('Medio', 'Alto') THEN c.provider_id END) AS providers_with_alerts
FROM claims c
LEFT JOIN claim_risk_results r ON r.claim_id = c.claim_id;

CREATE OR REPLACE VIEW vw_provider_alerts AS
SELECT
  p.provider_id,
  p.provider_name,
  COUNT(c.claim_id) AS claims,
  SUM(CASE WHEN r.risk_level IN ('Medio', 'Alto') THEN 1 ELSE 0 END) AS alerts,
  ROUND(AVG(r.risk_score), 1) AS avg_score,
  SUM(c.claim_amount) AS total_amount
FROM providers p
LEFT JOIN claims c ON c.provider_id = p.provider_id
LEFT JOIN claim_risk_results r ON r.claim_id = c.claim_id
GROUP BY p.provider_id, p.provider_name;

CREATE OR REPLACE VIEW vw_city_alerts AS
SELECT
  c.city,
  COUNT(c.claim_id) AS claims,
  SUM(CASE WHEN r.risk_level = 'Alto' THEN 1 ELSE 0 END) AS red_cases,
  ROUND(AVG(r.risk_score), 1) AS avg_score
FROM claims c
LEFT JOIN claim_risk_results r ON r.claim_id = c.claim_id
GROUP BY c.city;

-- Carga sugerida desde CSV, ajustando la ruta local:
-- LOAD DATA LOCAL INFILE 'backend/data/synthetic_customers.csv'
-- INTO TABLE customers
-- CHARACTER SET utf8mb4
-- FIELDS TERMINATED BY ',' ENCLOSED BY '"'
-- LINES TERMINATED BY '\n'
-- IGNORE 1 ROWS;
