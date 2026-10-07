from __future__ import annotations

import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "")
pool = ConnectionPool(
    conninfo=DATABASE_URL,
    kwargs={"row_factory": dict_row},
    min_size=1,
    max_size=10,
    open=False,
)


def _prepare(sql: str, params: tuple[Any, ...] | list[Any]) -> tuple[str, tuple[Any, ...]]:
    """Translate the existing PostgreSQL $1 placeholders and preserve repeats."""
    indexes = [int(match.group(1)) - 1 for match in re.finditer(r"\$(\d+)", sql)]
    statement = re.sub(r"\$(\d+)", "%s", sql)
    if not indexes:
        return statement, tuple(params)
    return statement, tuple(params[index] for index in indexes)


def query(sql: str, params: tuple[Any, ...] | list[Any] = (), conn=None) -> list[dict[str, Any]]:
    statement, values = _prepare(sql, params)
    if conn is None:
        with pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(statement, values)
                return list(cursor.fetchall()) if cursor.description else []
    with conn.cursor() as cursor:
        cursor.execute(statement, values)
        return list(cursor.fetchall()) if cursor.description else []


def query_many(sql: str, params_rows: list[tuple[Any, ...]], conn) -> None:
    if not params_rows:
        return
    statement, _ = _prepare(sql, params_rows[0])
    values = [_prepare(sql, params)[1] for params in params_rows]
    with conn.cursor() as cursor:
        cursor.executemany(statement, values)


@contextmanager
def transaction() -> Iterator[Any]:
    with pool.connection() as conn:
        with conn.transaction():
            yield conn
