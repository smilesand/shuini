from contextlib import asynccontextmanager
import logging
from pathlib import Path
import secrets
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from core.logging_utils import (
    bind_request_id,
    configure_logging,
    install_global_exception_logging,
    reset_request_id,
    summarize_request_body,
    to_log_text,
)
from routers import auth, calc, diagnostics, exchange, projects, records, recycle_bin
from core.config import get_settings
from database import init_db


settings = get_settings()
FRONTEND_DIST = Path(settings.frontend_dist).resolve() if settings.frontend_dist else None
LOG_PATHS = configure_logging(
    settings.log_level,
    settings.log_dir,
    max_bytes=settings.log_max_bytes,
    backup_count=settings.log_backup_count,
)
install_global_exception_logging()
logger = logging.getLogger("wtcmd.backend")
request_logger = logging.getLogger("wtcmd.request")


def _client_host(request: Request) -> str:
    return request.client.host if request.client else "-"


async def _request_body_summary(request: Request) -> str:
    if request.method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
        return "-"

    try:
        body = await request.body()
    except Exception:
        return "<body read failed>"

    return summarize_request_body(body, request.headers.get("content-type"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Application startup title=%s version=%s host=%s port=%s db_path=%s frontend_dist=%s log_dir=%s",
        settings.app_title,
        settings.app_version,
        settings.host,
        settings.port,
        settings.db_path,
        str(FRONTEND_DIST) if FRONTEND_DIST else "-",
        LOG_PATHS["log_dir"],
    )
    init_db()
    logger.info("Database initialized")
    try:
        yield
    finally:
        logger.info("Application shutdown complete")


app = FastAPI(title=settings.app_title, version=settings.app_version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def trace_requests(request: Request, call_next):
    request_id = request.headers.get("X-Client-Request-ID") or secrets.token_hex(8)
    request.state.request_id = request_id
    request.state.client_session_id = request.headers.get("X-Client-Session-ID") or "-"
    request.state.body_summary = await _request_body_summary(request)

    request_context = bind_request_id(request_id)
    started_at = time.perf_counter()
    request_logger.info(
        (
            "Request started method=%s path=%s query=%s client=%s client_session=%s "
            "user_agent=%s body=%s"
        ),
        request.method,
        request.url.path,
        request.url.query or "-",
        _client_host(request),
        request.state.client_session_id,
        request.headers.get("user-agent", "-"),
        request.state.body_summary,
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - started_at) * 1000
        request_logger.exception(
            "Request crashed before response method=%s path=%s duration_ms=%.2f client=%s",
            request.method,
            request.url.path,
            duration_ms,
            _client_host(request),
        )
        reset_request_id(request_context)
        raise

    duration_ms = (time.perf_counter() - started_at) * 1000
    response.headers["X-Request-ID"] = request_id
    request_logger.info(
        "Request completed method=%s path=%s status=%s duration_ms=%.2f client=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        _client_host(request),
    )
    reset_request_id(request_context)
    return response

app.include_router(calc.router,     prefix="/api", tags=["calculation"])
app.include_router(auth.router,     prefix="/api", tags=["auth"])
app.include_router(diagnostics.router, prefix="/api", tags=["diagnostics"])
app.include_router(records.router,  prefix="/api", tags=["records"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(exchange.router, prefix="/api", tags=["import-export"])


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 异常 → 统一错误格式"""
    request_logger.warning(
        "HTTPException method=%s path=%s status=%s detail=%s body=%s",
        request.method,
        request.url.path,
        exc.status_code,
        to_log_text(exc.detail),
        getattr(request.state, "body_summary", "-"),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail), "data": None},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """兜底异常 → 统一 500 格式"""
    logger.exception(
        "Unhandled exception method=%s path=%s client=%s body=%s",
        request.method,
        request.url.path,
        _client_host(request),
        getattr(request.state, "body_summary", "-"),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )


def _frontend_asset(path: str) -> Path | None:
    if FRONTEND_DIST is None or not FRONTEND_DIST.exists():
        return None

    candidate = (FRONTEND_DIST / path.lstrip("/")).resolve()
    try:
        candidate.relative_to(FRONTEND_DIST)
    except ValueError:
        return None

    return candidate if candidate.is_file() else None


if FRONTEND_DIST is None:
    @app.get("/")
    def root():
        return {"message": "水泥配比计算 API 运行中", "docs": "/docs"}
else:
    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        asset = _frontend_asset(full_path)
        if asset is not None:
            return FileResponse(asset)

        index_file = _frontend_asset("index.html")
        if index_file is None:
            raise HTTPException(status_code=404, detail="前端资源不存在")

        return FileResponse(index_file)


if __name__ == "__main__":
    import uvicorn

    logger.info(
        "Starting uvicorn host=%s port=%s log_level=%s app_log=%s error_log=%s",
        settings.host,
        settings.port,
        settings.log_level,
        LOG_PATHS["app_log"],
        LOG_PATHS["error_log"],
    )
    config = uvicorn.Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    try:
        server.run()
    except KeyboardInterrupt:
        # Uvicorn has already completed graceful shutdown; suppress the extra traceback.
        pass
