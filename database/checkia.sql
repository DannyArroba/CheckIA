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

-- HackIAthon 2026 - dataset multi-hoja + PDFs
CREATE TABLE IF NOT EXISTS siniestros (
  id_siniestro VARCHAR(30) PRIMARY KEY,
  id_poliza VARCHAR(30),
  id_asegurado VARCHAR(30),
  fecha_siniestro DATE,
  fecha_reporte DATE,
  ramo VARCHAR(80),
  placa VARCHAR(30),
  cobertura VARCHAR(120),
  ciudad VARCHAR(100),
  sucursal VARCHAR(100),
  id_proveedor VARCHAR(30),
  descripcion_evento TEXT,
  docs_completos BOOLEAN,
  proveedor_lista_restrictiva BOOLEAN,
  dias_ocurrencia_reporte INT,
  dias_desde_inicio_poliza INT,
  dias_hasta_fin_poliza INT,
  reclamos_previos INT,
  suma_asegurada DECIMAL(14,2),
  similitud_narrativa_max DECIMAL(8,4),
  numero_parte_policial VARCHAR(80),
  monto_reclamado DECIMAL(14,2),
  monto_estimado DECIMAL(14,2),
  monto_pagado DECIMAL(14,2),
  estado VARCHAR(80),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS polizas (
  id_poliza VARCHAR(30) PRIMARY KEY,
  id_asegurado VARCHAR(30),
  ramo VARCHAR(80),
  fecha_inicio DATE,
  fecha_fin DATE,
  suma_asegurada DECIMAL(14,2),
  prima_anual DECIMAL(14,2),
  canal_venta VARCHAR(100),
  estado_poliza VARCHAR(80)
);

CREATE TABLE IF NOT EXISTS asegurados (
  id_asegurado VARCHAR(30) PRIMARY KEY,
  nombres_asegurado VARCHAR(180),
  segmento VARCHAR(80),
  ciudad VARCHAR(100),
  antiguedad VARCHAR(80),
  polizas_activas INT,
  reclamos_ultimos_12_meses INT,
  reclamos_historico_total INT,
  reclamos_rc_sin_tercero INT,
  perfil_riesgo_historico VARCHAR(80)
);

CREATE TABLE IF NOT EXISTS proveedores_hackia (
  id_proveedor VARCHAR(30) PRIMARY KEY,
  nombre_proveedor VARCHAR(180),
  tipo VARCHAR(80),
  ciudad VARCHAR(100),
  siniestros_asociados INT,
  en_lista_restrictiva BOOLEAN,
  motivo_restriccion TEXT,
  observacion_proveedor TEXT,
  promedio_monto DECIMAL(14,2)
);

CREATE TABLE IF NOT EXISTS documentos (
  id_documento VARCHAR(30) PRIMARY KEY,
  id_siniestro VARCHAR(30),
  tipo_documento VARCHAR(120),
  nombre_archivo_pdf VARCHAR(255),
  pdf_no_encontrado BOOLEAN NOT NULL DEFAULT FALSE,
  documento_no_listado_en_excel BOOLEAN NOT NULL DEFAULT FALSE,
  ruta_archivo VARCHAR(500),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_documentos_siniestro (id_siniestro),
  INDEX idx_documentos_archivo (nombre_archivo_pdf)
);

CREATE TABLE IF NOT EXISTS documentos_extraidos (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_documento VARCHAR(30),
  id_siniestro VARCHAR(30),
  tipo_documento VARCHAR(120),
  nombre_archivo VARCHAR(255),
  ruta_archivo VARCHAR(500),
  metodo_extraccion VARCHAR(40),
  texto_extraido LONGTEXT,
  campos_extraidos JSON,
  ocr_usado BOOLEAN NOT NULL DEFAULT FALSE,
  documento_no_listado_en_excel BOOLEAN NOT NULL DEFAULT FALSE,
  pdf_no_encontrado BOOLEAN NOT NULL DEFAULT FALSE,
  procesado_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_doc_file (nombre_archivo),
  INDEX idx_extraidos_siniestro (id_siniestro),
  INDEX idx_extraidos_documento (id_documento)
);

CREATE TABLE IF NOT EXISTS facturas (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_documento VARCHAR(30),
  id_siniestro VARCHAR(30),
  numero_factura VARCHAR(80),
  fecha DATE,
  taller_proveedor VARCHAR(180),
  ruc VARCHAR(20),
  cliente VARCHAR(180),
  placa VARCHAR(30),
  vehiculo VARCHAR(160),
  subtotal DECIMAL(14,2),
  iva DECIMAL(14,2),
  total_pagar DECIMAL(14,2),
  descripciones_reparacion TEXT,
  documento_alterado BOOLEAN NOT NULL DEFAULT FALSE,
  caso_marcado VARCHAR(60),
  INDEX idx_facturas_siniestro (id_siniestro)
);

CREATE TABLE IF NOT EXISTS partes_policiales (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_documento VARCHAR(30),
  id_siniestro VARCHAR(30),
  numero_parte_policial VARCHAR(80),
  fecha DATE,
  hora VARCHAR(40),
  lugar VARCHAR(180),
  placa VARCHAR(30),
  marca VARCHAR(80),
  modelo VARCHAR(80),
  motor VARCHAR(120),
  chasis VARCHAR(120),
  tipo_accidente VARCHAR(100),
  consecuencias VARCHAR(180),
  clima VARCHAR(80),
  vehiculos_involucrados TEXT,
  narrativa_accidente TEXT,
  autoridad_agente VARCHAR(180),
  observaciones_relevantes TEXT,
  INDEX idx_partes_siniestro (id_siniestro)
);

CREATE TABLE IF NOT EXISTS declaraciones_accidente (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_documento VARCHAR(30),
  id_siniestro VARCHAR(30),
  asegurado VARCHAR(180),
  telefono VARCHAR(80),
  direccion VARCHAR(220),
  poliza VARCHAR(80),
  placa VARCHAR(30),
  marca VARCHAR(80),
  modelo VARCHAR(80),
  color VARCHAR(60),
  chasis VARCHAR(120),
  motor VARCHAR(120),
  fecha_accidente DATE,
  hora VARCHAR(40),
  lugar VARCHAR(180),
  velocidad VARCHAR(80),
  descripcion_accidente TEXT,
  responsable_conductor VARCHAR(180),
  datos_contrario TEXT,
  intervencion_autoridades VARCHAR(120),
  lugar_asistencia_medica VARCHAR(180),
  INDEX idx_declaraciones_siniestro (id_siniestro)
);

CREATE TABLE IF NOT EXISTS alertas_fraude (
  id_alerta BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_siniestro VARCHAR(30),
  tipo_alerta VARCHAR(120),
  severidad ENUM('baja', 'media', 'alta', 'critica') NOT NULL,
  explicacion TEXT,
  fuente_evidencia VARCHAR(80),
  campo_detectado VARCHAR(120),
  valor_esperado TEXT,
  valor_encontrado TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_alertas_siniestro (id_siniestro),
  INDEX idx_alertas_severidad (severidad)
);

CREATE TABLE IF NOT EXISTS analisis_fraude (
  id_siniestro VARCHAR(30) PRIMARY KEY,
  puntaje_riesgo INT NOT NULL,
  nivel_riesgo ENUM('Bajo', 'Medio', 'Alto', 'Critico') NOT NULL,
  explicacion TEXT,
  factores JSON,
  calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS hackia_import_logs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  tipo VARCHAR(60),
  mensaje TEXT,
  detalle JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

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
