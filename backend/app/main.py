import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api import growth, retrospectives, statistics, tasks
from app.core.config import get_settings
from app.core.errors import DomainError

app = FastAPI(title="Dayly API", version="0.2.1", description="개인용 할 일 · 고정 회고 · 성장 기록")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(tasks.router, prefix="/api")
app.include_router(statistics.router, prefix="/api")
app.include_router(retrospectives.router, prefix="/api")
app.include_router(growth.router, prefix="/api")


@app.exception_handler(DomainError)
def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=404 if exc.code.endswith("_not_found") else 403,
        content={"code": exc.code, "detail": exc.message},
    )


@app.exception_handler(SQLAlchemyError)
def database_error_handler(request: Request, exc: SQLAlchemyError):
    logging.getLogger(__name__).exception("Database request failed", exc_info=exc)
    return JSONResponse(status_code=503, content={
        "code": "database_unavailable", "detail": "저장소에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.",
    })
