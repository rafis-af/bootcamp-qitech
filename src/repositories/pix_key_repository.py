from typing import Optional

from database import Context
from models import Account, PixKey


class PixKeyRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, account: Account, key_type: str, key_value: str) -> PixKey:
        pix_key = PixKey()

        pix_key.account = account
        pix_key.key_type = key_type
        pix_key.key_value = key_value

        self.session.add(pix_key)
        return pix_key

    def get_by_value(self, key_value: str) -> Optional[PixKey]:
        return self.session.query(PixKey).filter(PixKey.key_value == key_value).first()

    def count_by_account(self, account: Account) -> int:
        return self.session.query(PixKey).filter(PixKey.account_id == account.id).count()

    def list_by_account(self, account: Account) -> list:
        return (
            self.session.query(PixKey)
            .filter(PixKey.account_id == account.id)
            .order_by(PixKey.created_at.asc(), PixKey.id.asc())
            .all()
        )
