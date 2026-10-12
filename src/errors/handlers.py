from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from errors.base_error import (
    QIException,
    InternalError,
    InvalidBodyType,
    InvalidJson,
    InvalidParameter,
    InvalidSchema,
    MethodNotAllowed,
    MissingBody,
    NotFoundResource,
    UnsupportedMediaType,
)
from errors.unexpected import is_bug, map_unexpected_exception
from utils.logger import get_logger
from utils.request_context import get_request_id

logger = get_logger(__name__)

BODY_TYPE_ERRORS = {"dict_type", "model_attributes_type"}
JSON_MEDIA_TYPE = "application/json"


def qi_exception_to_response(exception: QIException) -> JSONResponse:
    body = {
        "title": exception.title,
        "description": exception.description,
        "translation": exception.translation,
        "code": exception.code,
    }

    field = getattr(exception, "field", None)
    if field:
        body["field"] = field

    return JSONResponse(status_code=exception.http_status, content=body)


def describe_validation_error(error: dict) -> str:
    location = []
    for part in error.get("loc", []):
        if part not in ("body", "query"):
            location.append(str(part))

    message = error.get("msg", "invalid value")

    if location:
        return f"{message} in {'.'.join(location)}"

    return message


def is_json_content_type(content_type: str = None) -> bool:
    """Aceita "application/json" com ou sem parâmetros ("; charset=utf-8")."""
    if not content_type:
        return False

    return content_type.split(";")[0].strip().lower() == JSON_MEDIA_TYPE


def validation_error_to_qi_exception(error: dict, content_type: str = None) -> QIException:
    """O FastAPI só valida o corpo como "um dict"; o resto é do jsonschema.

    Então o que cai aqui é sempre um destes: o corpo não é JSON, não veio,
    não é um objeto, ou veio num Content-Type que não é JSON. Cada um tem a
    sua mensagem: sem o Content-Type certo, o FastAPI nem tenta ler o corpo
    como JSON, e "não é um objeto" seria uma mensagem enganosa.
    """
    error_type = error.get("type")
    location = tuple(error.get("loc", ()))
    origin = location[0] if location else ""

    if error_type == "json_invalid":
        position = location[1] if len(location) > 1 else None
        return InvalidJson(position)

    if origin == "body" and error_type == "missing":
        return MissingBody()

    if origin == "body" and error_type in BODY_TYPE_ERRORS:
        if not is_json_content_type(content_type):
            return UnsupportedMediaType()
        return InvalidBodyType()

    description = describe_validation_error(error)

    if origin in ("query", "path"):
        return InvalidParameter(description)

    return InvalidSchema(description)


def log_unexpected(request: Request, error: Exception, mapped: QIException) -> None:
    where = f"{request.method} {request.url.path}"

    if is_bug(mapped):
        logger.exception(f"Erro inesperado em {where}", exc_info=error)
    else:
        logger.error(f"{mapped.code} {mapped.title} em {where}: {type(error).__name__}: {error}")


def register_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(QIException)
    def handle_qi_exception(request: Request, exception: QIException) -> JSONResponse:
        return qi_exception_to_response(exception)

    @application.exception_handler(StarletteHTTPException)
    def handle_http_exception(request: Request, exception: StarletteHTTPException) -> JSONResponse:
        if exception.status_code == 404:
            return qi_exception_to_response(NotFoundResource(request.method, request.url.path))

        if exception.status_code == 405:
            allowed = (exception.headers or {}).get("Allow", "")
            allowed_methods = [method.strip() for method in allowed.split(",") if method.strip()]
            return qi_exception_to_response(MethodNotAllowed(request.method, request.url.path, allowed_methods))

        if 400 <= exception.status_code < 500:
            detail = str(exception.detail)
            return qi_exception_to_response(InvalidSchema(detail, f"Requisição inválida: {detail}"))

        logger.error(f"HTTP {exception.status_code} em {request.url.path}: {exception.detail}")
        return qi_exception_to_response(InternalError(get_request_id()))

    @application.exception_handler(RequestValidationError)
    def handle_validation_error(request: Request, exception: RequestValidationError) -> JSONResponse:
        errors = exception.errors()

        if errors:
            first_error = errors[0]
        else:
            first_error = {}

        content_type = request.headers.get("content-type")

        return qi_exception_to_response(validation_error_to_qi_exception(first_error, content_type))

    @application.exception_handler(Exception)
    def handle_unexpected_error(request: Request, exception: Exception) -> JSONResponse:
        # Última rede. O normal é o session_manager já ter convertido o erro
        # (e aí a resposta sai com o X-Request-ID e entra no log de saída).
        mapped = map_unexpected_exception(exception, get_request_id())
        log_unexpected(request, exception, mapped)
        return qi_exception_to_response(mapped)
