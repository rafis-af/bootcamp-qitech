import hmac

from fastapi import FastAPI, Request

from constants import BYPASS_ENDPOINTS, INTERNAL_TOKEN
from errors.base_error import ForbiddenNotInternal
from errors.handlers import qi_exception_to_response


def token_is_valid(received_token: str) -> bool:
    # compare_digest leva o mesmo tempo acerte ou erre o começo do token:
    # quem tenta adivinhar não aprende nada medindo a demora da resposta.
    return hmac.compare_digest(received_token.encode("utf-8"), INTERNAL_TOKEN.encode("utf-8"))


def register_internal_token_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def check_internal_token(request: Request, call_next):
        is_public = request.url.path in BYPASS_ENDPOINTS

        if request.method == "OPTIONS" or is_public:
            return await call_next(request)

        received_token = request.headers.get("INTERNAL-TOKEN")

        if received_token is None:
            return qi_exception_to_response(ForbiddenNotInternal(token_was_sent=False))

        if not token_is_valid(received_token):
            return qi_exception_to_response(ForbiddenNotInternal(token_was_sent=True))

        return await call_next(request)
