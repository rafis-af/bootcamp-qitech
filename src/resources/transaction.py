from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import TransactionController
from utils.schema_handler import SchemaHandler


def operation_response(operation: dict) -> JSONResponse:
    status_code = http_status.HTTP_201_CREATED
    if operation["is_replay"]:
        status_code = http_status.HTTP_200_OK

    return JSONResponse(
        content=jsonable_encoder(operation["transaction"]),
        status_code=status_code,
    )


class TransactionResource:
    @SchemaHandler.validate("post_deposit.json")
    def on_post_deposit(self, account_key: str, payload: dict) -> JSONResponse:
        controller = TransactionController()
        operation = controller.deposit(account_key, payload)

        return operation_response(operation)

    @SchemaHandler.validate("post_transfer.json")
    def on_post_transfer(self, account_key: str, payload: dict) -> JSONResponse:
        controller = TransactionController()
        operation = controller.transfer(account_key, payload)

        return operation_response(operation)

    @SchemaHandler.validate("post_pix.json")
    def on_post_pix(self, account_key: str, payload: dict) -> JSONResponse:
        controller = TransactionController()
        operation = controller.send_pix(account_key, payload)

        return operation_response(operation)
