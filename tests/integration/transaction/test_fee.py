import pytest

from tests.utils import DbUtils, MockScenario, ObjectGenerator, PayloadGenerator, RequestGenerator

INITIAL_FEE = 150
NEW_SILVER_TRANSFER_FEE = 200


def transfer(origin_key: str, destination_key: str, amount: int) -> tuple:
    payload = PayloadGenerator.create_transfer_payload(destination_key, amount)
    return RequestGenerator.POST_transfer(origin_key, payload)


class TestFee:
    """Tarifa dinâmica (RFC 2.1): mudar o preço é mudar um dado, sem deploy.

    A tarifa vale para todo cliente Prata, inclusive os dos outros testes.
    Por isso este teste é `exclusive`: roda sozinho (veja tests/conftest.py)
    e devolve a tarifa antiga no fim.
    """

    @pytest.mark.exclusive
    def test_new_fee_applies_from_now_on_and_old_operations_keep_theirs(self):
        silver = ObjectGenerator.create_funded_account(100000, MockScenario.SILVER)
        gold = ObjectGenerator.create_funded_account(100000)
        destination = ObjectGenerator.create_account()
        pix_key = ObjectGenerator.create_pix_key(destination["account_key"])

        status, before_change = transfer(silver["account_key"], destination["account_key"], 1000)
        assert status == 201
        assert before_change["fee"] == INITIAL_FEE

        try:
            DbUtils.change_fee("silver", "transfer", NEW_SILVER_TRANSFER_FEE)

            # A tarifa nova vale para transferência do Prata, e só para ela.
            status, response = transfer(silver["account_key"], destination["account_key"], 1000)
            assert status == 201
            assert response["fee"] == NEW_SILVER_TRANSFER_FEE

            status, response = transfer(gold["account_key"], destination["account_key"], 1000)
            assert response["fee"] == INITIAL_FEE

            pix_payload = PayloadGenerator.create_pix_payload(pix_key["key_value"], 1000)
            status, response = RequestGenerator.POST_pix(silver["account_key"], pix_payload)
            assert response["fee"] == INITIAL_FEE

            # A operação de antes da troca continua dizendo quanto pagou.
            fee_entries = [
                entry for entry in ObjectGenerator.get_full_statement(silver["account_key"])
                if entry["entry_type"] == "fee"
            ]
            fees_by_transaction = {entry["transaction_key"]: entry["amount"] for entry in fee_entries}
            assert fees_by_transaction[before_change["transaction_key"]] == -INITIAL_FEE

            ObjectGenerator.assert_balance_matches_statement(silver["account_key"])
        finally:
            DbUtils.change_fee("silver", "transfer", INITIAL_FEE)
