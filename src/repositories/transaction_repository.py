from datetime import datetime
from typing import Optional

from sqlalchemy import func

from database import Context
from models import Account, Deposit, Fee, PixKey, Transaction, TransactionType


class TransactionRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(
        self,
        transaction_key: str,
        transaction_type: TransactionType,
        origin_account: Optional[Account],
        destination_account: Account,
        amount: int,
        applied_fee: Optional[Fee],
        fee_amount: int,
        pix_key: Optional[PixKey] = None,
        above_income: bool = False,
    ) -> Transaction:
        transaction = Transaction()

        transaction.transaction_key = transaction_key
        transaction.transaction_type = transaction_type
        transaction.origin_account = origin_account
        transaction.destination_account = destination_account
        transaction.pix_key = pix_key
        transaction.amount = amount
        transaction.applied_fee = applied_fee
        transaction.fee = fee_amount
        transaction.above_income = above_income

        self.session.add(transaction)
        return transaction

    def create_deposit(self, transaction: Transaction, deposit_data: dict) -> Deposit:
        deposit = Deposit()

        deposit.transaction = transaction
        deposit.method = deposit_data["method"]
        deposit.depositor_name = deposit_data["depositor_name"]
        deposit.depositor_document_number = deposit_data["depositor_document_number"]
        deposit.source_bank_code = deposit_data.get("source_bank_code")

        self.session.add(deposit)
        return deposit

    def get_by_key(self, transaction_key: str) -> Optional[Transaction]:
        return self.session.query(Transaction).filter(Transaction.transaction_key == transaction_key).first()

    def sum_outflows(self, account: Account, start: datetime, end: datetime) -> int:
        total = (
            self.session.query(func.coalesce(func.sum(Transaction.amount), 0))
            .filter(
                Transaction.origin_account_id == account.id,
                Transaction.created_at >= start,
                Transaction.created_at < end,
            )
            .scalar()
        )
        return int(total)

    def count_above_income(self, account: Account, start: datetime, end: datetime) -> int:
        return (
            self.session.query(Transaction)
            .filter(
                Transaction.origin_account_id == account.id,
                Transaction.above_income.is_(True),
                Transaction.created_at >= start,
                Transaction.created_at < end,
            )
            .count()
        )
