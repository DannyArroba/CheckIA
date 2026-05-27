from __future__ import annotations

import os
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from backend.src.ingestion.load_data import load_all_data


def _config() -> dict:
    return {
        "enabled": os.getenv("DB_ENABLED", "true").lower() == "true",
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "checkia"),
    }


def get_connection():
    config = _config()
    if not config["enabled"]:
        raise RuntimeError("La conexión a base de datos está desactivada.")
    return pymysql.connect(
        host=config["host"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        database=config["database"],
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
    )


def database_status() -> dict:
    config = _config()
    if not config["enabled"]:
        return {"enabled": False, "connected": False, "database": config["database"]}
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT DATABASE() AS database_name, VERSION() AS version")
                row = cursor.fetchone()
        return {
            "enabled": True,
            "connected": True,
            "host": config["host"],
            "port": config["port"],
            "database": row["database_name"],
            "version": row["version"],
        }
    except Exception as exc:
        return {
            "enabled": True,
            "connected": False,
            "host": config["host"],
            "port": config["port"],
            "database": config["database"],
            "error": str(exc),
        }


def ensure_runtime_schema() -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_conversations (
                  conversation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  title VARCHAR(160) NOT NULL,
                  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS claim_review_actions (
                  review_id BIGINT AUTO_INCREMENT PRIMARY KEY,
                  claim_id VARCHAR(20) NOT NULL,
                  status ENUM('pendiente', 'bajo_observacion', 'documentacion_solicitada', 'revisado_sin_alerta', 'derivado_analista') NOT NULL,
                  note TEXT,
                  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  INDEX idx_review_claim (claim_id)
                )
                """
            )
            cursor.execute("SHOW COLUMNS FROM agent_messages LIKE 'sort_order'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE agent_messages ADD COLUMN sort_order INT NOT NULL DEFAULT 0")
            cursor.execute("SHOW COLUMNS FROM agent_messages LIKE 'conversation_id'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE agent_messages ADD COLUMN conversation_id BIGINT NULL AFTER message_id")
                cursor.execute("INSERT INTO agent_conversations (title) VALUES ('Chat anterior')")
                cursor.execute("SELECT LAST_INSERT_ID() AS conversation_id")
                conversation_id = cursor.fetchone()["conversation_id"]
                cursor.execute("UPDATE agent_messages SET conversation_id=%s WHERE conversation_id IS NULL", (conversation_id,))
        connection.commit()


def _bool(value: Any) -> int:
    if isinstance(value, str):
        return 1 if value.lower() in {"true", "1", "si", "sí"} else 0
    return 1 if bool(value) else 0


def sync_source_tables() -> dict:
    data = load_all_data()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            cursor.execute("DELETE FROM claim_rule_results")
            cursor.execute("DELETE FROM claim_risk_results")
            cursor.execute("DELETE FROM claim_documents")
            cursor.execute("DELETE FROM claims")
            cursor.execute("DELETE FROM policies")
            cursor.execute("DELETE FROM customers")
            cursor.execute("DELETE FROM providers")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
            cursor.executemany(
                """
                INSERT INTO customers (customer_id, anonymous_customer, city, age_range, segment, recent_customer_change)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  anonymous_customer=VALUES(anonymous_customer), city=VALUES(city),
                  age_range=VALUES(age_range), segment=VALUES(segment),
                  recent_customer_change=VALUES(recent_customer_change)
                """,
                [
                    (
                        r.customer_id,
                        r.anonymous_customer,
                        r.city,
                        r.age_range,
                        r.segment,
                        _bool(r.recent_customer_change),
                    )
                    for r in data["customers"].itertuples()
                ],
            )
            cursor.executemany(
                """
                INSERT INTO providers (provider_id, provider_name, provider_type, provider_city, restricted_simulated)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  provider_name=VALUES(provider_name), provider_type=VALUES(provider_type),
                  provider_city=VALUES(provider_city), restricted_simulated=VALUES(restricted_simulated)
                """,
                [
                    (
                        r.provider_id,
                        r.provider_name,
                        r.provider_type,
                        r.provider_city,
                        _bool(r.restricted_simulated),
                    )
                    for r in data["providers"].itertuples()
                ],
            )
            cursor.executemany(
                """
                INSERT INTO policies (policy_id, customer_id, line, policy_start_date, policy_end_date, insured_amount, premium_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  customer_id=VALUES(customer_id), line=VALUES(line),
                  policy_start_date=VALUES(policy_start_date), policy_end_date=VALUES(policy_end_date),
                  insured_amount=VALUES(insured_amount), premium_status=VALUES(premium_status)
                """,
                [
                    (
                        r.policy_id,
                        r.customer_id,
                        r.line,
                        r.policy_start_date,
                        r.policy_end_date,
                        float(r.insured_amount),
                        r.premium_status,
                    )
                    for r in data["policies"].itertuples()
                ],
            )
            cursor.executemany(
                """
                INSERT INTO claims (
                  claim_id, policy_id, customer_id, anonymous_customer, vehicle_id, provider_id,
                  line, coverage, city, claim_date, report_date, claim_amount, narrative, recent_customer_change
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  policy_id=VALUES(policy_id), customer_id=VALUES(customer_id),
                  anonymous_customer=VALUES(anonymous_customer), vehicle_id=VALUES(vehicle_id),
                  provider_id=VALUES(provider_id), line=VALUES(line), coverage=VALUES(coverage),
                  city=VALUES(city), claim_date=VALUES(claim_date), report_date=VALUES(report_date),
                  claim_amount=VALUES(claim_amount), narrative=VALUES(narrative),
                  recent_customer_change=VALUES(recent_customer_change)
                """,
                [
                    (
                        r.claim_id,
                        r.policy_id,
                        r.customer_id,
                        r.anonymous_customer,
                        None if str(r.vehicle_id) == "nan" else r.vehicle_id,
                        r.provider_id,
                        r.line,
                        r.coverage,
                        r.city,
                        r.claim_date,
                        r.report_date,
                        float(r.claim_amount),
                        r.narrative,
                        _bool(r.recent_customer_change),
                    )
                    for r in data["claims"].itertuples()
                ],
            )
            cursor.execute("DELETE FROM claim_documents")
            cursor.executemany(
                "INSERT INTO claim_documents (claim_id, document_type, status) VALUES (%s, %s, %s)",
                [(r.claim_id, r.document_type, r.status) for r in data["documents"].itertuples()],
            )
        connection.commit()
    return {name: int(len(frame)) for name, frame in data.items()}


def sync_risk_results(claims) -> dict:
    ensure_runtime_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM claim_rule_results")
            cursor.execute("DELETE FROM claim_risk_results")
            risk_rows = []
            rule_rows = []
            for row in claims.itertuples():
                explanation = row.explainability.get("explicacion", "") if isinstance(row.explainability, dict) else ""
                risk_rows.append(
                    (
                        row.claim_id,
                        float(row.rule_score),
                        float(row.model_score),
                        float(row.nlp_score),
                        int(row.risk_score),
                        row.risk_level,
                        row.risk_color,
                        row.recommended_action,
                        explanation,
                    )
                )
                for rule in row.rules:
                    rule_rows.append(
                        (
                            row.claim_id,
                            rule["codigo"],
                            rule["nombre"],
                            int(rule["puntos"]),
                            rule["severidad"],
                            rule["explicacion"],
                        )
                    )
            cursor.executemany(
                """
                INSERT INTO claim_risk_results (
                  claim_id, rule_score, model_score, nlp_score, risk_score,
                  risk_level, risk_color, recommended_action, explanation
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                risk_rows,
            )
            if rule_rows:
                cursor.executemany(
                    """
                    INSERT INTO claim_rule_results (
                      claim_id, rule_code, rule_name, points, severity, explanation
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    rule_rows,
                )
        connection.commit()
    return {"risk_results": len(risk_rows), "rule_results": len(rule_rows)}


def create_agent_conversation(title: str = "Nuevo chat") -> int | None:
    try:
        ensure_runtime_schema()
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO agent_conversations (title) VALUES (%s)", (title[:160],))
                conversation_id = cursor.lastrowid
            connection.commit()
        return int(conversation_id)
    except Exception:
        return None


def list_agent_conversations() -> list[dict]:
    ensure_runtime_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.conversation_id, c.title, c.created_at, c.updated_at,
                       COUNT(m.message_id) AS message_count
                FROM agent_conversations c
                LEFT JOIN agent_messages m ON m.conversation_id = c.conversation_id
                GROUP BY c.conversation_id, c.title, c.created_at, c.updated_at
                ORDER BY c.updated_at DESC, c.conversation_id DESC
                LIMIT 60
                """
            )
            return cursor.fetchall()


def delete_agent_conversation(conversation_id: int) -> None:
    ensure_runtime_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM agent_messages WHERE conversation_id=%s", (conversation_id,))
            cursor.execute("DELETE FROM agent_conversations WHERE conversation_id=%s", (conversation_id,))
        connection.commit()


def rename_agent_conversation(conversation_id: int, title: str) -> None:
    ensure_runtime_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE agent_conversations SET title=%s WHERE conversation_id=%s", (title[:160], conversation_id))
        connection.commit()


def save_agent_message(role: str, message_text: str, provider: str = "sistema", conversation_id: int | None = None) -> int | None:
    try:
        ensure_runtime_schema()
        if conversation_id is None:
            conversation_id = create_agent_conversation("Nuevo chat")
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order FROM agent_messages WHERE conversation_id=%s", (conversation_id,))
                next_order = cursor.fetchone()["next_order"]
                cursor.execute(
                    "INSERT INTO agent_messages (conversation_id, role, message_text, provider, sort_order) VALUES (%s, %s, %s, %s, %s)",
                    (conversation_id, role, message_text, provider, next_order),
                )
                if role == "usuario" and next_order == 1:
                    title = message_text.strip().replace("\n", " ")[:60] or "Nuevo chat"
                    cursor.execute("UPDATE agent_conversations SET title=%s WHERE conversation_id=%s", (title, conversation_id))
                cursor.execute("UPDATE agent_conversations SET updated_at=CURRENT_TIMESTAMP WHERE conversation_id=%s", (conversation_id,))
            connection.commit()
        return int(conversation_id)
    except Exception:
        return conversation_id


def list_agent_messages(conversation_id: int | None = None) -> list[dict]:
    ensure_runtime_schema()
    if conversation_id is None:
        conversations = list_agent_conversations()
        conversation_id = conversations[0]["conversation_id"] if conversations else create_agent_conversation("Nuevo chat")
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT message_id, conversation_id, role, message_text, provider, sort_order, created_at
                FROM agent_messages
                WHERE conversation_id=%s
                ORDER BY sort_order ASC, message_id ASC
                LIMIT 200
                """,
                (conversation_id,),
            )
            return cursor.fetchall()


def delete_agent_message(message_id: int) -> None:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM agent_messages WHERE message_id=%s", (message_id,))
        connection.commit()


def move_agent_message(message_id: int, direction: str) -> None:
    ensure_runtime_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT message_id, conversation_id, sort_order FROM agent_messages WHERE message_id=%s", (message_id,))
            current = cursor.fetchone()
            if not current:
                return
            operator = "<" if direction == "up" else ">"
            order = "DESC" if direction == "up" else "ASC"
            cursor.execute(
                f"""
                SELECT message_id, sort_order FROM agent_messages
                WHERE conversation_id=%s AND sort_order {operator} %s
                ORDER BY sort_order {order}
                LIMIT 1
                """,
                (current["conversation_id"], current["sort_order"]),
            )
            other = cursor.fetchone()
            if not other:
                return
            cursor.execute("UPDATE agent_messages SET sort_order=%s WHERE message_id=%s", (other["sort_order"], current["message_id"]))
            cursor.execute("UPDATE agent_messages SET sort_order=%s WHERE message_id=%s", (current["sort_order"], other["message_id"]))
        connection.commit()


def save_claim_review_action(claim_id: str, status: str, note: str | None = None) -> dict:
    ensure_runtime_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO claim_review_actions (claim_id, status, note) VALUES (%s, %s, %s)",
                (claim_id, status, note),
            )
            review_id = cursor.lastrowid
        connection.commit()
    return {"review_id": int(review_id), "claim_id": claim_id, "status": status, "note": note}


def get_claim_review_actions(claim_id: str) -> list[dict]:
    ensure_runtime_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT review_id, claim_id, status, note, created_at
                FROM claim_review_actions
                WHERE claim_id=%s
                ORDER BY created_at DESC, review_id DESC
                """,
                (claim_id,),
            )
            return cursor.fetchall()


def get_latest_review_actions(claim_ids: list[str] | None = None) -> dict[str, dict]:
    ensure_runtime_schema()
    params: tuple = ()
    filter_sql = ""
    if claim_ids:
        placeholders = ", ".join(["%s"] * len(claim_ids))
        filter_sql = f"WHERE claim_id IN ({placeholders})"
        params = tuple(claim_ids)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT a.review_id, a.claim_id, a.status, a.note, a.created_at
                FROM claim_review_actions a
                INNER JOIN (
                  SELECT claim_id, MAX(review_id) AS review_id
                  FROM claim_review_actions
                  {filter_sql}
                  GROUP BY claim_id
                ) latest ON latest.review_id = a.review_id
                ORDER BY a.created_at DESC, a.review_id DESC
                """,
                params,
            )
            return {row["claim_id"]: row for row in cursor.fetchall()}


def review_actions_summary(limit: int = 12) -> list[dict]:
    ensure_runtime_schema()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.review_id, a.claim_id, a.status, a.note, a.created_at
                FROM claim_review_actions a
                INNER JOIN (
                  SELECT claim_id, MAX(review_id) AS review_id
                  FROM claim_review_actions
                  GROUP BY claim_id
                ) latest ON latest.review_id = a.review_id
                ORDER BY a.created_at DESC, a.review_id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cursor.fetchall()
