from typing import NoReturn, Optional

from controllers.base_controller import BaseController
from errors import AccountBlocked, NotFoundAccount, QIException, WrongPassword
from models import Account, Client, Event, Status, Transaction
from repositories import AccountRepository, CatalogRepository, EventRepository
from utils.password import password_matches

MAX_PASSWORD_ATTEMPTS = 3


class BaseAccountController(BaseController):
    def __init__(self, class_name: str) -> None:
        super().__init__(class_name)
        self.account_repository = AccountRepository(self.context)
        self.catalog_repository = CatalogRepository(self.context)
        self.event_repository = EventRepository(self.context)

    def _get_account(self, account_key: str) -> Account:
        account = self.account_repository.get_by_key(account_key)

        if account is None:
            raise NotFoundAccount(account_key)

        return account

    def _lock_accounts(self, *accounts: Account) -> None:
        account_ids = sorted({account.id for account in accounts})

        for account_id in account_ids:
            self.account_repository.lock(account_id)

    def _check_active(self, account: Account, detail: dict) -> None:
        if account.status.enumerator == Status.BLOCKED:
            self._refuse_with_event(AccountBlocked(account.account_key), account=account, detail=detail)

    def _authenticate(self, account: Account, password: str) -> None:
        if password_matches(password, account.password_hash):
            self.account_repository.reset_failed_password_attempts(account)
            return

        self.account_repository.increment_failed_password_attempts(account)
        self._record_event(
            Event.PASSWORD_FAILED,
            Event.WARNING,
            account=account,
            detail={"failed_password_attempts": account.failed_password_attempts},
        )

        if account.failed_password_attempts >= MAX_PASSWORD_ATTEMPTS:
            self._block(account, Event.REASON_PASSWORD)
            self._refuse(AccountBlocked(account.account_key))

        self._refuse(WrongPassword(MAX_PASSWORD_ATTEMPTS - account.failed_password_attempts))

    def _block(self, account: Account, reason: str) -> None:
        blocked_status = self.catalog_repository.get_status(Status.BLOCKED)
        self.account_repository.update_status(account, blocked_status)

        self._record_event(Event.ACCOUNT_BLOCKED, Event.CRITICAL, account=account, detail={"reason": reason})

    def _record_event(
        self,
        event_type: str,
        severity: str,
        account: Optional[Account] = None,
        transaction: Optional[Transaction] = None,
        detail: Optional[dict] = None,
        client: Optional[Client] = None,
    ) -> None:
        if client is None and account is not None:
            client = account.client

        self.event_repository.create(event_type, severity, client, account, transaction, detail)

    def _refuse(self, error: QIException) -> NoReturn:
        self.session.commit()
        raise error

    def _refuse_with_event(
        self,
        error: QIException,
        account: Optional[Account] = None,
        transaction: Optional[Transaction] = None,
        detail: Optional[dict] = None,
    ) -> NoReturn:
        event_detail = {"code": error.code, "reason": error.title}

        if detail is not None:
            event_detail.update(detail)

        self._record_event(
            Event.OPERATION_REFUSED,
            Event.WARNING,
            account=account,
            transaction=transaction,
            detail=event_detail,
        )
        self._refuse(error)
