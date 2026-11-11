"""REST: translating errors into the Problem Details format (RFC 9457)."""

from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from services import ServiceError

BASE = "https://example.com/problems/"

# service error code -> (HTTP status, end of the type address, title)
PROBLEMS = {
    "EMAIL_TAKEN": (409, "email-taken", "Email already in use"),
    "ALREADY_ENROLLED": (409, "already-enrolled", "Already enrolled"),
    "COURSE_NOT_FOUND": (404, "course-not-found", "Course not found"),
    "STUDENT_NOT_FOUND": (404, "student-not-found", "Student not found"),
}


def problem(
    request: Request,
    status: int,
    title: str,
    detail: str | None = None,
    type: str = "about:blank",
    headers: dict | None = None,
    **extra,
) -> JSONResponse:
    body = {"type": type, "title": title, "status": status}
    if detail is not None:
        body["detail"] = detail
    body["instance"] = request.url.path
    body.update(extra)
    return JSONResponse(
        body,
        status_code=status,
        headers=headers,
        media_type="application/problem+json",
    )


def install(app: FastAPI) -> None:
    @app.exception_handler(ServiceError)
    async def on_service_error(request: Request, exc: ServiceError):
        status, slug, title = PROBLEMS[exc.code]
        return problem(request, status, title, exc.message, type=BASE + slug)

    @app.exception_handler(StarletteHTTPException)
    async def on_http_error(request: Request, exc: StarletteHTTPException):
        title = HTTPStatus(exc.status_code).phrase
        detail = exc.detail if exc.detail != title else None
        return problem(request, exc.status_code, title, detail, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def on_validation_error(request: Request, exc: RequestValidationError):
        errors = [
            {
                "in": err["loc"][0],
                "field": ".".join(str(part) for part in err["loc"][1:]),
                "detail": err["msg"],
            }
            for err in exc.errors()
        ]
        text = f"{len(errors)} invalid value(s) in the request"
        return problem(
            request,
            422,
            "Validation failed",
            text,
            type=BASE + "validation-error",
            errors=errors,
        )
