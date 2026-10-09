from typing import Optional

from sqlalchemy.exc import IntegrityError

from controllers.base_account_controller import BaseAccountController
from dtos import TransactionDTO
from errors import (
    DailyLimitExceeded,
    IncomeLimitExceeded,
    InsufficientBalance,
    InvalidDocumentNumber,
    NotFoundPixKey,
    SameAccountTransfer,
    TransactionKeyConflict,
)
from models import Account, Entry, Event, Level, PixKey, Transaction, TransactionType
from repositories import EntryRepository, PixKeyRepository, TransactionRepository
from utils import clock
from utils.document_number import is_valid_cpf

OUTFLOW_ENTRY_TYPES = {
    TransactionType.TRANSFER: (Entry.TRANSFER_OUT, Entry.TRANSFER_IN),
    TransactionType.PIX: (Entry.PIX_OUT, Entry.PIX_IN),
}


class TransactionController(BaseAccountController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.transaction_repository = TransactionRepository(self.context)
        self.entry_repository = EntryRepository(self.context)
        self.pix_key_repository = PixKeyRepository(self.context)

    def deposit(self, account_key: str, deposit_data: dict) -> dict:
        self.logger.debug(f"Depositando na conta {account_key}")

        transaction_key = deposit_data["transaction_key"].lower()
        amount = self._amount_of(deposit_data)

        depositor_document_number = deposit_data["depositor_document_number"]
        if not is_valid_cpf(depositor_document_number):
            raise InvalidDocumentNumber(depositor_document_number)

        requested = {
            "transaction_type": TransactionType.DEPOSIT,
            "origin_account_key": None,
            "destination_account_key": account_key,
            "amount": amount,
        }

        replay = self._find_replay(transaction_key, requested, account_key)
        if replay is not None:
            return replay

        account = self._get_account(account_key)
        self._lock_accounts(account)

        replay = self._find_replay(transaction_key, requested, account_key)
        if replay is not None:
            return replay

        self._check_active(account, self._operation_detail(transaction_key, requested))

        deposit_type = self.catalog_repository.get_transaction_type(TransactionType.DEPOSIT)

        transaction = self.transaction_repository.create(
            transaction_key=transaction_key,
            transaction_type=deposit_type,
            origin_account=None,
            destination_account=account,
            amount=amount,
            applied_fee=None,
            fee_amount=0,
        )
        self.transaction_repository.create_deposit(transaction, deposit_data)
        self.entry_repository.post(transaction, account, Entry.DEPOSIT, amount)

        return self._save(transaction, requested, account_key)

    def transfer(self, origin_account_key: str, transfer_data: dict) -> dict:
        self.logger.debug(f"Transferindo da conta {origin_account_key}")

        transaction_key = transfer_data["transaction_key"].lower()
        destination_account_key = transfer_data["destination_account_key"]
        amount = self._amount_of(transfer_data)

        requested = {
            "transaction_type": TransactionType.TRANSFER,
            "origin_account_key": origin_account_key,
            "destination_account_key": destination_account_key,
            "amount": amount,
        }

        replay = self._find_replay(transaction_key, requested, origin_account_key)
        if replay is not None:
            return replay

        origin = self._get_account(origin_account_key)
        destination = self._get_account(destination_account_key)

        if origin.id == destination.id:
            raise SameAccountTransfer(origin_account_key)

        return self._send_money(transaction_key, requested, origin, destination, transfer_data["password"])

    def send_pix(self, origin_account_key: str, pix_data: dict) -> dict:
        self.logger.debug(f"Enviando um Pix da conta {origin_account_key}")

        transaction_key = pix_data["transaction_key"].lower()
        amount = self._amount_of(pix_data)

        pix_key_value = pix_data["pix_key"].lower()

        requested = {
            "transaction_type": TransactionType.PIX,
            "origin_account_key": origin_account_key,
            "pix_key": pix_key_value,
            "amount": amount,
        }

        replay = self._find_replay(transaction_key, requested, origin_account_key)
        if replay is not None:
            return replay

        origin = self._get_account(origin_account_key)

        pix_key = self.pix_key_repository.get_by_value(pix_key_value)

        if pix_key is None:
            raise NotFoundPixKey(pix_key_value)

        destination = pix_key.account

        if origin.id == destination.id:
            raise SameAccountTransfer(origin_account_key)

        return self._send_money(transaction_key, requested, origin, destination, pix_data["password"], pix_key)

    def _send_money(
        self,
        transaction_key: str,
        requested: dict,
        origin: Account,
        destination: Account,
        password: str,
        pix_key: Optional[PixKey] = None,
    ) -> dict:
        transaction_type_enumerator = requested["transaction_type"]
        amount = requested["amount"]

        detail = self._operation_detail(transaction_key, requested)
        detail["destination_account_key"] = destination.account_key

        self._lock_accounts(origin, destination)

        replay = self._find_replay(transaction_key, requested, origin.account_key)
        if replay is not None:
            return replay

        self._check_active(origin, detail)
        self._check_active(destination, detail)
        self._authenticate(origin, password)

        level = origin.client.level
        self._check_daily_limit(origin, level, amount, detail)

        transaction_type = self.catalog_repository.get_transaction_type(transaction_type_enumerator)
        fee = self.catalog_repository.get_current_fee(level, transaction_type)

        fee_amount = 0
        if fee is not None:
            fee_amount = fee.amount

        if origin.balance < amount + fee_amount:
            self._refuse_with_event(
                InsufficientBalance(origin.balance, amount, fee_amount),
                account=origin,
                detail=detail,
            )

        above_income = self._check_income(origin, level, amount, detail)

        transaction = self.transaction_repository.create(
            transaction_key=transaction_key,
            transaction_type=transaction_type,
            origin_account=origin,
            destination_account=destination,
            amount=amount,
            applied_fee=fee,
            fee_amount=fee_amount,
            pix_key=pix_key,
            above_income=above_income,
        )

        out_entry_type, in_entry_type = OUTFLOW_ENTRY_TYPES[transaction_type_enumerator]

        self.entry_repository.post(transaction, origin, out_entry_type, -amount)
        if fee_amount > 0:
            self.entry_repository.post(transaction, origin, Entry.FEE, -fee_amount)
        self.entry_repository.post(transaction, destination, in_entry_type, amount)

        if above_income:
            self._record_event(
                Event.INCOME_ALERT,
                Event.WARNING,
                account=origin,
                transaction=transaction,
                detail={
                    "amount": amount,
                    "monthly_income": origin.client.monthly_income,
                    "income_multiple": level.income_multiple,
                },
            )

        return self._save(transaction, requested, origin.account_key)

    def _check_daily_limit(self, origin: Account, level: Level, amount: int, detail: dict) -> None:
        if level.daily_outflow_limit is None:
            return

        start, end = clock.today_range()
        sent_today = self.transaction_repository.sum_outflows(origin, start, end)

        if sent_today + amount > level.daily_outflow_limit:
            self._refuse_with_event(
                DailyLimitExceeded(level.daily_outflow_limit, sent_today, amount),
                account=origin,
                detail=detail,
            )

    def _check_income(self, origin: Account, level: Level, amount: int, detail: dict) -> bool:
        income_limit = origin.client.monthly_income * level.income_multiple

        if amount <= income_limit:
            return False

        start, end = clock.current_month_range()
        alerts_this_month = self.transaction_repository.count_above_income(origin, start, end)

        if alerts_this_month >= level.income_alerts_per_month:
            self._block(origin, Event.REASON_INCOME)
            self._refuse_with_event(
                IncomeLimitExceeded(level.income_alerts_per_month),
                account=origin,
                detail=detail,
            )

        return True

    def _find_replay(self, transaction_key: str, requested: dict, account_key: str) -> Optional[dict]:
        existing = self.transaction_repository.get_by_key(transaction_key)

        if existing is None:
            return None

        return self._replay_or_refuse(existing, requested, account_key)

    def _replay_or_refuse(self, existing: Transaction, requested: dict, account_key: str) -> dict:
        if self._is_same_operation(existing, requested):
            self.logger.info(f"Operação {existing.transaction_key} repetida: devolvendo a original")
            return {"transaction": TransactionDTO.obj_to_dict(existing), "is_replay": True}

        account = self.account_repository.get_by_key(account_key)

        self._refuse_with_event(
            TransactionKeyConflict(existing.transaction_key),
            account=account,
            transaction=existing,
            detail=self._operation_detail(existing.transaction_key, requested),
        )

    def _is_same_operation(self, existing: Transaction, requested: dict) -> bool:
        stored = {
            "transaction_type": existing.transaction_type.enumerator,
            "origin_account_key": None,
            "destination_account_key": existing.destination_account.account_key,
            "pix_key": None,
            "amount": existing.amount,
        }

        if existing.origin_account is not None:
            stored["origin_account_key"] = existing.origin_account.account_key

        if existing.pix_key is not None:
            stored["pix_key"] = existing.pix_key.key_value

        for field, value in requested.items():
            if stored[field] != value:
                return False

        return True

    def _save(self, transaction: Transaction, requested: dict, account_key: str) -> dict:
        transaction_key = transaction.transaction_key

        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()

            existing = self.transaction_repository.get_by_key(transaction_key)

            if existing is None:
                raise

            return self._replay_or_refuse(existing, requested, account_key)

        transaction_dto = TransactionDTO.obj_to_dict(transaction)
        self.session.commit()

        return {"transaction": transaction_dto, "is_replay": False}

    def _operation_detail(self, transaction_key: str, requested: dict) -> dict:
        detail = {"transaction_key": transaction_key}
        detail.update(requested)

        return detail

    def _amount_of(self, operation_data: dict) -> int:
        return int(operation_data["amount"])
