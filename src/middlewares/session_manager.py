from fastapi import FastAPI, Request

from database import clear_context, open_context
from errors.handlers import log_unexpected, qi_exception_to_response
from errors.unexpected import map_unexpected_exception
from utils.logger import get_logger
from utils.request_context import get_request_id

logger = get_logger(__name__)


def register_session_manager_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def manage_session(request: Request, call_next):
        context = open_context()

        try:
            response = await call_next(request)
        except Exception as error:
            # Erro que ninguém tratou: desfaz o que estava aberto e responde
            # AQUI, para a resposta ainda passar pelos middlewares de fora
            # (o log de saída e o X-Request-ID). Sem isso, o 500 saía sem
            # o id da requisição, e não dava para achar o erro no log.
            rollback_quietly(context)
            mapped = map_unexpected_exception(error, get_request_id())
            log_unexpected(request, error, mapped)
            response = qi_exception_to_response(mapped)
        finally:
            if context.db_session is not None:
                try:
                    context.db_session.close()
                except Exception as error:
                    logger.warning(f"Não consegui fechar a sessão do banco: {type(error).__name__}: {error}")

            clear_context()

        return response


def rollback_quietly(context) -> None:
    """Com o banco fora do ar, o próprio rollback falha. Isso não pode
    esconder o erro original, que é o que vira a resposta."""
    if context.db_session is None:
        return

    try:
        context.db_session.rollback()
    except Exception as error:
        logger.warning(f"Rollback falhou: {type(error).__name__}: {error}")
