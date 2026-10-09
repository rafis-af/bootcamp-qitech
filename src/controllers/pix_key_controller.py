from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from controllers.base_account_controller import BaseAccountController
from dtos import PixKeyDTO
from errors import PixKeyAlreadyRegistered, PixKeyLimitReached, PixKeyNotOwnDocument
from models import PixKey
from repositories import PixKeyRepository

MAX_PIX_KEYS_PER_ACCOUNT = 5


class PixKeyController(BaseAccountController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.pix_key_repository = PixKeyRepository(self.context)

    def create(self, account_key: str, pix_key_data: dict) -> dict:
        self.logger.debug(f"Cadastrando uma chave Pix na conta {account_key}")

        key_type = pix_key_data["key_type"]

        if key_type == PixKey.RANDOM:
            key_value = str(uuid4())
        else:
            key_value = pix_key_data["key_value"].lower()

        account = self._get_account(account_key)
        self._lock_accounts(account)

        self._check_active(account, {"operation": "create_pix_key", "key_type": key_type})
        self._authenticate(account, pix_key_data["password"])

        if self.pix_key_repository.get_by_value(key_value) is not None:
            self._refuse(PixKeyAlreadyRegistered(key_value))

        if key_type == PixKey.CPF and key_value != account.client.document_number:
            self._refuse(PixKeyNotOwnDocument())

        if self.pix_key_repository.count_by_account(account) >= MAX_PIX_KEYS_PER_ACCOUNT:
            self._refuse(PixKeyLimitReached(MAX_PIX_KEYS_PER_ACCOUNT))

        pix_key = self.pix_key_repository.create(account, key_type, key_value)

        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            raise PixKeyAlreadyRegistered(key_value)

        pix_key_dto = PixKeyDTO.obj_to_dict(pix_key)
        self.session.commit()

        return pix_key_dto

    def get_list(self, account_key: str) -> list:
        account = self._get_account(account_key)
        pix_keys_list = self.pix_key_repository.list_by_account(account)

        return PixKeyDTO.list_obj_to_list_dict(pix_keys_list)
