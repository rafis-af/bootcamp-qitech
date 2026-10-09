from os import environ

from tests.utils.requisition import ClientRequisition


INTERNAL_TOKEN = environ.get("INTERNAL_TOKEN", "default_token")

HEADERS = {"INTERNAL-TOKEN": INTERNAL_TOKEN}


def send(method: str, endpoint: str, payload: dict = None, query_params: dict = None) -> tuple:
    response = ClientRequisition.send(
        method,
        endpoint,
        payload=payload,
        headers=dict(HEADERS),
        query_params=query_params,
    )
    return response.response_status, response.response_json


class RequestGenerator:
    """Uma função por rota da API (RFC, seção 4). Cada uma devolve (status, corpo)."""

    # Cliente
    @staticmethod
    def POST_client(client_payload: dict) -> tuple:
        return send("POST", "/client", payload=client_payload)

    @staticmethod
    def GET_client(client_key: str) -> tuple:
        return send("GET", f"/client/{client_key}")

    @staticmethod
    def GET_clients(params: dict = None) -> tuple:
        return send("GET", "/clients", query_params=params)

    # Conta
    @staticmethod
    def POST_account(client_key: str, account_payload: dict) -> tuple:
        return send("POST", f"/client/{client_key}/account", payload=account_payload)

    @staticmethod
    def GET_account(account_key: str) -> tuple:
        return send("GET", f"/account/{account_key}")

    @staticmethod
    def PUT_account_status(account_key: str, status_payload: dict) -> tuple:
        return send("PUT", f"/account/{account_key}/status", payload=status_payload)

    # Dinheiro
    @staticmethod
    def POST_deposit(account_key: str, deposit_payload: dict) -> tuple:
        return send("POST", f"/account/{account_key}/deposit", payload=deposit_payload)

    @staticmethod
    def POST_transfer(account_key: str, transfer_payload: dict) -> tuple:
        return send("POST", f"/account/{account_key}/transfer", payload=transfer_payload)

    # Pix
    @staticmethod
    def POST_pix_key(account_key: str, pix_key_payload: dict) -> tuple:
        return send("POST", f"/account/{account_key}/pix-key", payload=pix_key_payload)

    @staticmethod
    def GET_pix_keys(account_key: str) -> tuple:
        return send("GET", f"/account/{account_key}/pix-keys")

    @staticmethod
    def POST_pix(account_key: str, pix_payload: dict) -> tuple:
        return send("POST", f"/account/{account_key}/pix", payload=pix_payload)

    # Extrato
    @staticmethod
    def GET_statement(account_key: str, params: dict = None) -> tuple:
        return send("GET", f"/account/{account_key}/statement", query_params=params)
