from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import PixKeyController
from utils.schema_handler import SchemaHandler


class PixKeyResource:
    @SchemaHandler.validate("post_pix_key.json")
    def on_post(self, account_key: str, payload: dict) -> JSONResponse:
        controller = PixKeyController()
        pix_key = controller.create(account_key, payload)

        return JSONResponse(
            content=jsonable_encoder(pix_key),
            status_code=http_status.HTTP_201_CREATED,
        )

    def on_get_list(self, account_key: str) -> JSONResponse:
        controller = PixKeyController()
        pix_keys = controller.get_list(account_key)

        return JSONResponse(
            content=jsonable_encoder({"data": pix_keys}),
            status_code=http_status.HTTP_200_OK,
        )
