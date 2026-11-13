import logging
import os
from typing import Any

import mysql.connector
from fastapi import FastAPI, HTTPException, Query
from mysql.connector import Error as MySQLError
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

app = FastAPI(title="Kubernetes Course Tasks API", version="1.0.0")


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=1000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message content cannot be blank")
        return value


def get_db_connection() -> Any:
    password = os.getenv("MYSQL_PASSWORD")
    if password is None:
        raise HTTPException(status_code=503, detail="MySQL is not configured")

    try:
        return mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "mysql"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "app"),
            password=password,
            database=os.getenv("MYSQL_DATABASE", "app"),
            connection_timeout=5,
        )
    except MySQLError as exc:
        logger.exception("Could not connect to MySQL")
        raise HTTPException(status_code=503, detail="MySQL is unavailable") from exc


def ensure_messages_table(cursor: Any) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            content VARCHAR(1000) NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def raise_database_error(exc: MySQLError) -> None:
    logger.exception("MySQL query failed")
    raise HTTPException(status_code=503, detail="MySQL is unavailable") from exc


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "FastAPI service is running", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        try:
            cursor.execute("SELECT 1")
        finally:
            cursor.close()
    except MySQLError as exc:
        raise_database_error(exc)
    finally:
        connection.close()
    return {"status": "ok", "database": "ok"}


@app.get("/api/info")
def info() -> dict[str, Any]:
    return {
        "name": app.title,
        "version": app.version,
        "endpoints": ["/", "/health", "/api/info", "/api/messages"],
    }


@app.get("/api/messages")
def list_messages(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, list[dict[str, Any]]]:
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            ensure_messages_table(cursor)
            cursor.execute(
                "SELECT id, content, created_at FROM messages "
                "ORDER BY id DESC LIMIT %s",
                (limit,),
            )
            messages = cursor.fetchall()
        finally:
            cursor.close()
    except MySQLError as exc:
        raise_database_error(exc)
    finally:
        connection.close()
    return {"messages": messages}


@app.post("/api/messages", status_code=201)
def create_message(message: MessageCreate) -> dict[str, Any]:
    connection = get_db_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            ensure_messages_table(cursor)
            cursor.execute(
                "INSERT INTO messages (content) VALUES (%s)",
                (message.content,),
            )
            message_id = cursor.lastrowid
            cursor.execute(
                "SELECT id, content, created_at FROM messages WHERE id = %s",
                (message_id,),
            )
            created_message = cursor.fetchone()
            connection.commit()
        finally:
            cursor.close()
    except MySQLError as exc:
        raise_database_error(exc)
    finally:
        connection.close()
    return created_message