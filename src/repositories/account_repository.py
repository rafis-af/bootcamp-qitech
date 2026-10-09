from typing import Optional
from uuid import uuid4

from database import Context
from models import Account, Client, Status


class AccountRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, client: Client, password_hash: str, status: Status) -> Account:
        account = Account()

        account.account_key = str(uuid4())
        account.client = client
        account.status = status
        account.balance = 0
        account.password_hash = password_hash
        account.failed_password_attempts = 0

        self.session.add(account)
        return account

    def get_by_key(self, account_key: str) -> Optional[Account]:
        return self.session.query(Account).filter(Account.account_key == account_key).first()

    def lock(self, account_id: int) -> Account:
        return (
            self.session.query(Account)
            .filter(Account.id == account_id)
            .with_for_update()
            .populate_existing()
            .one()
        )

    def update_status(self, account: Account, status: Status) -> None:
        account.status = status

    def increment_failed_password_attempts(self, account: Account) -> None:
        account.failed_password_attempts = account.failed_password_attempts + 1

    def reset_failed_password_attempts(self, account: Account) -> None:
        account.failed_password_attempts = 0
