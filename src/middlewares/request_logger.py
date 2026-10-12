import time
from urllib.parse import parse_qsl, urlencode

from fastapi import FastAPI, Request

from constants import BYPASS_ENDPOINTS
from utils.logger import get_logger

logger = get_logger(__name__)

# Filtros da listagem de clientes que são dado pessoal (LGPD): o log
# registra que o filtro foi usado, mas não o valor.
SENSITIVE_QUERY_PARAMS = {"document_number", "email", "name"}
MASK = "***"


def masked_query(raw_query: str) -> str:
    params = []
    for name, value in parse_qsl(raw_query, keep_blank_values=True):
        if name in SENSITIVE_QUERY_PARAMS:
            value = MASK
        params.append((name, value))

    return urlencode(params, safe="*")


def register_request_logger_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def log_request(request: Request, call_next):
        if request.url.path in BYPASS_ENDPOINTS:
            return await call_next(request)

        requested_path = request.url.path
        if request.url.query:
            requested_path = f"{requested_path}?{masked_query(request.url.query)}"

        started_at = time.perf_counter()
        logger.info(f"ENTROU {request.method} {requested_path}")

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.info(f"SAIU {response.status_code} {request.method} {request.url.path} - {elapsed_ms:.1f} ms")

        return response
