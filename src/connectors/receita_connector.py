from connectors.rest_connector import BaseConnectorResponse, RestConnector
from constants import RECEITA_API_INTERNAL_TOKEN, RECEITA_API_TIMEOUT, RECEITA_API_URL


class ReceitaConnector(RestConnector):
    def __init__(self) -> None:
        super().__init__(
            class_name=__name__,
            service_name="Receita",
            base_url=RECEITA_API_URL,
            timeout=RECEITA_API_TIMEOUT,
            internal_token=RECEITA_API_INTERNAL_TOKEN,
        )

    def get_document_situation(self, document_number: str) -> BaseConnectorResponse:
        payload = {"document_number": document_number}

        return self.send(endpoint="/cpf", method="POST", payload=payload)
