from models import Transaction, TransactionType
from utils.clock import to_local_isoformat


class TransactionDTO:
    @staticmethod
    def obj_to_dict(transaction: Transaction) -> dict:
        dto = dict()
        dto["transaction_key"] = transaction.transaction_key
        dto["transaction_type"] = transaction.transaction_type.enumerator

        dto["origin_account_key"] = None
        if transaction.origin_account is not None:
            dto["origin_account_key"] = transaction.origin_account.account_key

        dto["destination_account_key"] = transaction.destination_account.account_key
        dto["amount"] = transaction.amount
        dto["fee"] = transaction.fee
        dto["above_income"] = transaction.above_income
        dto["created_at"] = to_local_isoformat(transaction.created_at)

        if transaction.transaction_type.enumerator == TransactionType.PIX:
            dto["pix_key"] = {
                "key_type": transaction.pix_key.key_type,
                "key_value": transaction.pix_key.key_value,
            }
            dto["destination_name"] = transaction.destination_account.client.name

        if transaction.transaction_type.enumerator == TransactionType.DEPOSIT:
            deposit = transaction.deposit
            dto["deposit"] = {
                "method": deposit.method,
                "depositor_name": deposit.depositor_name,
                "depositor_document_number": deposit.depositor_document_number,
                "source_bank_code": deposit.source_bank_code,
            }

        return dto
