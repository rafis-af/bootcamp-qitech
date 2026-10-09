from typing import List

from models import PixKey
from utils.clock import to_local_isoformat


class PixKeyDTO:
    @staticmethod
    def obj_to_dict(pix_key: PixKey) -> dict:
        dto = dict()
        dto["key_type"] = pix_key.key_type
        dto["key_value"] = pix_key.key_value
        dto["created_at"] = to_local_isoformat(pix_key.created_at)

        return dto

    @staticmethod
    def list_obj_to_list_dict(pix_keys_list: List[PixKey]) -> List[dict]:
        pix_keys_dict_list = []

        for pix_key in pix_keys_list:
            pix_keys_dict_list.append(PixKeyDTO.obj_to_dict(pix_key))

        return pix_keys_dict_list
