"""Measuring instrument: SQL queries per HTTP request (X-SQL-Queries header)."""

from contextvars import ContextVar

from fastapi import FastAPI, Request
from sqlalchemy import event

from db import engine

# The counter is a list: threads and tasks created inside the request both see it.
_current: ContextVar[list[int] | None] = ContextVar("sql_counter", default=None)


@event.listens_for(engine, "before_cursor_execute")
def count_query(conn, cursor, statement, parameters, context, executemany):
    box = _current.get()
    if box is not None:
        box[0] += 1


def install(app: FastAPI) -> None:
    @app.middleware("http")
    async def add_sql_count(request: Request, call_next):
        box = [0]
        token = _current.set(box)
        try:
            response = await call_next(request)
        finally:
            _current.reset(token)
        response.headers["X-SQL-Queries"] = str(box[0])
        return response
