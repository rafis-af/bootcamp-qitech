from models import Account
from utils.clock import to_local_isoformat


class AccountDTO:
    @staticmethod
    def obj_to_dict(account: Account) -> dict:
        dto = dict()
        dto["account_key"] = account.account_key
        dto["client_key"] = account.client.client_key
        dto["name"] = account.client.name
        dto["balance"] = account.balance
        dto["status"] = account.status.enumerator
        dto["level"] = account.client.level.enumerator
        dto["created_at"] = to_local_isoformat(account.created_at)

        return dto
