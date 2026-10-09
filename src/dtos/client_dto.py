from typing import List

from models import Client
from utils.clock import to_local_isoformat


class ClientDTO:
    @staticmethod
    def obj_to_dict(client: Client) -> dict:
        client_dto = ClientDTO.obj_to_simplified_dict(client)

        client_dto["account_key"] = None
        if client.account is not None:
            client_dto["account_key"] = client.account.account_key

        return client_dto

    @staticmethod
    def obj_to_simplified_dict(client: Client) -> dict:
        dto = dict()
        dto["client_key"] = client.client_key
        dto["name"] = client.name
        dto["email"] = client.email
        dto["document_number"] = client.document_number
        dto["birthdate"] = client.birthdate.isoformat()
        dto["monthly_income"] = client.monthly_income
        dto["status"] = client.status.enumerator

        dto["level"] = None
        if client.level is not None:
            dto["level"] = client.level.enumerator

        dto["created_at"] = to_local_isoformat(client.created_at)

        return dto

    @staticmethod
    def list_obj_to_list_dict(clients_list: List[Client]) -> List[dict]:
        clients_dict_list = []

        for client in clients_list:
            clients_dict_list.append(ClientDTO.obj_to_simplified_dict(client))

        return clients_dict_list
