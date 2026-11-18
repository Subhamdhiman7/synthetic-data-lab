"""FastAPI application for Synthetic Data Lab."""

import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.routes import datasets, health, plans
from backend.schemas.responses import ErrorResponse, RootResponse


API_VERSION = "1.0.0"

app = FastAPI(
    title="Synthetic Data Lab API",
    version=API_VERSION,
    description="A thin REST layer around the existing Datagen engine.",
    docs_url="/docs",
    redoc_url="/redoc",
)

# This is intentionally local-only by default. Public deployments must replace
# this allow-list and add authentication, TLS, rate limiting, and audit logs.
configured_origins = os.getenv(
    "SYNTHETIC_DATA_LAB_FRONTEND_ORIGINS",
    "http://127.0.0.1:5173,http://localhost:5173",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in configured_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

MAX_REQUEST_BYTES = 128 * 1024


@app.middleware("http")
async def request_and_security_headers(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                return JSONResponse(
                    status_code=413,
                    content={"error": "request_too_large", "detail": "Request body is too large."},
                )
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_request", "detail": "Invalid Content-Length header."},
            )
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response

app.include_router(health.router)
app.include_router(datasets.router)
app.include_router(plans.router)


@app.get("/", response_model=RootResponse, tags=["meta"])
def root() -> RootResponse:
    return RootResponse(
        name="Synthetic Data Lab API",
        api_version=API_VERSION,
        docs="/docs",
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="validation_error",
            detail="Request validation failed.",
            fields=exc.errors(),
        ).model_dump(mode="json"),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="request_error",
            detail=str(exc.detail),
        ).model_dump(mode="json"),
    )
