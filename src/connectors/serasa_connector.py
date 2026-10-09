from connectors.rest_connector import BaseConnectorResponse, RestConnector
from constants import SERASA_API_INTERNAL_TOKEN, SERASA_API_TIMEOUT, SERASA_API_URL


class SerasaConnector(RestConnector):
    def __init__(self) -> None:
        super().__init__(
            class_name=__name__,
            service_name="Serasa",
            base_url=SERASA_API_URL,
            timeout=SERASA_API_TIMEOUT,
            internal_token=SERASA_API_INTERNAL_TOKEN,
        )

    def get_credit_report(self, document_number: str) -> BaseConnectorResponse:
        payload = {"document_number": document_number}

        return self.send(endpoint="/score", method="POST", payload=payload)
