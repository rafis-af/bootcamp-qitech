from fastapi import FastAPI

from constants import check_variables
from errors import register_error_handlers
from errors.base_error import error_verification
from middlewares import (
    register_internal_token_middleware,
    register_request_context_middleware,
    register_request_logger_middleware,
    register_session_manager_middleware,
)
from resources import (
    AccountResource,
    ClientResource,
    HealthCheckResource,
    PixKeyResource,
    TransactionResource,
)
from utils.logger import setup_logging


def create_app() -> FastAPI:
    application = FastAPI(
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    register_session_manager_middleware(application)
    register_internal_token_middleware(application)
    register_request_logger_middleware(application)
    register_request_context_middleware(application)

    health_check_resource = HealthCheckResource()
    client_resource = ClientResource()
    account_resource = AccountResource()
    transaction_resource = TransactionResource()
    pix_key_resource = PixKeyResource()

    application.add_api_route("/", health_check_resource.on_get_home, methods=["GET"])
    application.add_api_route(
        "/health_check",
        health_check_resource.on_get_health_check,
        methods=["GET"]
    )

    application.add_api_route(
        "/client",
        client_resource.on_post,
        methods=["POST"],
    )
    application.add_api_route(
        "/client/{client_key}",
        client_resource.on_get_by_key,
        methods=["GET"],
    )
    application.add_api_route(
        "/clients",
        client_resource.on_get_list,
        methods=["GET"],
    )

    application.add_api_route(
        "/client/{client_key}/account",
        account_resource.on_post,
        methods=["POST"],
    )
    application.add_api_route(
        "/account/{account_key}",
        account_resource.on_get_by_key,
        methods=["GET"],
    )
    application.add_api_route(
        "/account/{account_key}/status",
        account_resource.on_put_status,
        methods=["PUT"],
    )

    application.add_api_route(
        "/account/{account_key}/deposit",
        transaction_resource.on_post_deposit,
        methods=["POST"],
    )
    application.add_api_route(
        "/account/{account_key}/transfer",
        transaction_resource.on_post_transfer,
        methods=["POST"],
    )

    application.add_api_route(
        "/account/{account_key}/pix-key",
        pix_key_resource.on_post,
        methods=["POST"],
    )
    application.add_api_route(
        "/account/{account_key}/pix-keys",
        pix_key_resource.on_get_list,
        methods=["GET"],
    )
    application.add_api_route(
        "/account/{account_key}/pix",
        transaction_resource.on_post_pix,
        methods=["POST"],
    )

    application.add_api_route(
        "/account/{account_key}/statement",
        account_resource.on_get_statement,
        methods=["GET"],
    )

    register_error_handlers(application)

    return application


def main() -> FastAPI:
    check_variables()
    error_verification()
    setup_logging()

    return create_app()


app = main()
