from datetime import datetime
from typing import Optional

from database import Context
from models import Account, Entry, Transaction


class EntryRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def post(self, transaction: Transaction, account: Account, entry_type: str, amount: int) -> Entry:
        account.balance = account.balance + amount

        entry = Entry()
        entry.transaction = transaction
        entry.account = account
        entry.entry_type = entry_type
        entry.amount = amount
        entry.balance_after = account.balance

        self.session.add(entry)
        return entry

    def list_page(
        self,
        account: Account,
        limit: int,
        offset: int,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list:
        query = self.session.query(Entry).filter(Entry.account_id == account.id)

        if start is not None:
            query = query.filter(Entry.created_at >= start)

        if end is not None:
            query = query.filter(Entry.created_at < end)

        query = query.order_by(Entry.created_at.desc(), Entry.id.desc())

        return query.limit(limit + 1).offset(offset).all()
