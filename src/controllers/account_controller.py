from sqlalchemy.exc import IntegrityError

from controllers.base_account_controller import BaseAccountController
from dtos import AccountDTO, EntryDTO
from errors import (
    AccountStatusUnchanged,
    ClientAlreadyHasAccount,
    ClientBlocked,
    InvalidParameter,
    NotFoundClient,
)
from models import Account, Event, Status
from repositories import ClientRepository, EntryRepository
from utils import clock
from utils.password import hash_password


class AccountController(BaseAccountController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.client_repository = ClientRepository(self.context)
        self.entry_repository = EntryRepository(self.context)

    def create(self, client_key: str, account_data: dict) -> dict:
        self.logger.debug(f"Abrindo a conta do cliente {client_key}")

        client = self.client_repository.get_by_key(client_key)

        if client is None:
            raise NotFoundClient(client_key)

        if client.status.enumerator != Status.ACTIVE:
            raise ClientBlocked(client_key)

        if client.account is not None:
            raise ClientAlreadyHasAccount(client_key)

        password_hash = hash_password(account_data["password"])
        active_status = self.catalog_repository.get_status(Status.ACTIVE)

        account = self.account_repository.create(client, password_hash, active_status)
        self._record_event(Event.ACCOUNT_OPENED, Event.INFO, account=account)

        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            raise ClientAlreadyHasAccount(client_key)

        account_dto = AccountDTO.obj_to_dict(account)
        self.session.commit()

        return account_dto

    def get_by_key(self, account_key: str) -> dict:
        account = self._get_account(account_key)

        return AccountDTO.obj_to_dict(account)

    def update_status(self, account_key: str, new_status: str) -> dict:
        account = self._get_account(account_key)
        self._lock_accounts(account)

        if account.status.enumerator == new_status:
            raise AccountStatusUnchanged(account_key, new_status)

        if new_status == Status.BLOCKED:
            self._block(account, Event.REASON_MANUAL)
        else:
            self._unblock(account)

        account_dto = AccountDTO.obj_to_dict(account)
        self.session.commit()

        return account_dto

    def get_statement(self, account_key: str, limit: int, offset: int, filters: dict) -> dict:
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")

        if date_from is not None:
            date_from = clock.parse_date("date_from", date_from)

        if date_to is not None:
            date_to = clock.parse_date("date_to", date_to)

        if date_from is not None and date_to is not None and date_from > date_to:
            raise InvalidParameter(
                f"date_from ({date_from}) is after date_to ({date_to})",
                f"O período está invertido: date_from ({date_from}) é depois de date_to ({date_to}).",
                "date_from",
            )

        start = None
        if date_from is not None:
            start = clock.day_start(date_from)

        end = None
        if date_to is not None:
            end = clock.day_end(date_to)

        account = self._get_account(account_key)

        entries_list = self.entry_repository.list_page(account, limit, offset, start, end)

        is_last_page = True
        if len(entries_list) > limit:
            is_last_page = False
            entries_list = entries_list[:-1]

        return {
            "entries_list_dto": EntryDTO.list_obj_to_list_dict(entries_list),
            "is_last_page": is_last_page,
        }

    def _unblock(self, account: Account) -> None:
        active_status = self.catalog_repository.get_status(Status.ACTIVE)
        self.account_repository.update_status(account, active_status)
        self.account_repository.reset_failed_password_attempts(account)

        self._record_event(Event.ACCOUNT_UNBLOCKED, Event.INFO, account=account, detail={"reason": Event.REASON_MANUAL})
