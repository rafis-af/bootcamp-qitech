from fastapi import Request
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from constants import DEFAULT_LIMIT, DEFAULT_PAGE
from controllers import ClientController
from utils.schema_handler import SchemaHandler


class ClientResource:
    @SchemaHandler.validate("post_client.json")
    def on_post(self, payload: dict) -> JSONResponse:
        controller = ClientController()
        client = controller.create(payload)

        return JSONResponse(
            content=jsonable_encoder(client),
            status_code=http_status.HTTP_201_CREATED,
        )

    def on_get_by_key(self, client_key: str) -> JSONResponse:
        controller = ClientController()
        client = controller.get_by_key(client_key)

        return JSONResponse(
            content=jsonable_encoder(client),
            status_code=http_status.HTTP_200_OK,
        )

    @SchemaHandler.validate_query_params("get_clients.json")
    def on_get_list(self, request: Request) -> JSONResponse:
        controller = ClientController()

        query_params = request.query_params

        limit = int(query_params.get("limit", DEFAULT_LIMIT))
        page = int(query_params.get("page", DEFAULT_PAGE))

        filters = {
            "status_enumerators": query_params.getlist("status"),
            "level_enumerators": query_params.getlist("level"),
            "name": query_params.get("name"),
            "email": query_params.get("email"),
            "document_number": query_params.get("document_number"),
        }

        offset = page * limit
        clients_page = controller.get_list(limit, offset, filters)

        page_envelope = {
            "data": clients_page["clients_list_dto"],
            "limit": limit,
            "page": page,
            "is_last_page": clients_page["is_last_page"],
        }

        return JSONResponse(
            content=jsonable_encoder(page_envelope),
            status_code=http_status.HTTP_200_OK,
        )
