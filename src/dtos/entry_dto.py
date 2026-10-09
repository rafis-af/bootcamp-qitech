from typing import List

from models import Entry
from utils.clock import to_local_isoformat


class EntryDTO:
    @staticmethod
    def obj_to_dict(entry: Entry) -> dict:
        dto = dict()
        dto["entry_type"] = entry.entry_type
        dto["amount"] = entry.amount
        dto["balance_after"] = entry.balance_after
        dto["transaction_key"] = entry.transaction.transaction_key
        dto["transaction_type"] = entry.transaction.transaction_type.enumerator
        dto["created_at"] = to_local_isoformat(entry.created_at)

        return dto

    @staticmethod
    def list_obj_to_list_dict(entries_list: List[Entry]) -> List[dict]:
        entries_dict_list = []

        for entry in entries_list:
            entries_dict_list.append(EntryDTO.obj_to_dict(entry))

        return entries_dict_list
