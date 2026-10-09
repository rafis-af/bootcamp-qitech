from tests.utils import DbUtils, MockScenario, ObjectGenerator, PayloadGenerator, RequestGenerator

SILVER_DAILY_LIMIT = 100000
FEE = 150


def transfer(origin_key: str, destination_key: str, amount: int) -> tuple:
    payload = PayloadGenerator.create_transfer_payload(destination_key, amount)
    return RequestGenerator.POST_transfer(origin_key, payload)


class TestDailyLimit:
    """Limite diário de saídas do Prata: R$ 1.000,00, inclusive, sem a tarifa (RFC 2.1)."""

    def test_silver_reaches_the_limit_exactly_and_not_a_cent_more(self):
        origin = ObjectGenerator.create_funded_account(500000, MockScenario.SILVER)
        destination = ObjectGenerator.create_account()

        status, _response = transfer(origin["account_key"], destination["account_key"], 60000)
        assert status == 201

        # 60.000 + 40.000 = 100.000: o limite exato passa ("até o limite, inclusive").
        # Se a tarifa contasse, os R$ 1,50 da primeira já teriam estourado.
        status, _response = transfer(origin["account_key"], destination["account_key"], 40000)
        assert status == 201

        status, response = transfer(origin["account_key"], destination["account_key"], 1)
        assert status == 422
        assert response["code"] == "QIT001023"

        assert ObjectGenerator.get_balance(origin["account_key"]) == 500000 - SILVER_DAILY_LIMIT - 2 * FEE

        refusals = [
            event for event in DbUtils.events_of_account(origin["account_key"])
            if event["event_type"] == "operation_refused"
        ]
        assert refusals[0]["detail"]["code"] == "QIT001023"

    def test_transfers_and_pix_share_the_same_limit(self):
        origin = ObjectGenerator.create_funded_account(500000, MockScenario.SILVER)
        destination = ObjectGenerator.create_account()
        pix_key = ObjectGenerator.create_pix_key(destination["account_key"])

        status, _response = transfer(origin["account_key"], destination["account_key"], 99900)
        assert status == 201

        payload = PayloadGenerator.create_pix_payload(pix_key["key_value"], 101)
        status, response = RequestGenerator.POST_pix(origin["account_key"], payload)
        assert status == 422
        assert response["code"] == "QIT001023"

        payload = PayloadGenerator.create_pix_payload(pix_key["key_value"], 100)
        status, _response = RequestGenerator.POST_pix(origin["account_key"], payload)
        assert status == 201

    def test_deposits_do_not_count(self):
        origin = ObjectGenerator.create_funded_account(100000, MockScenario.SILVER)
        destination = ObjectGenerator.create_account()

        ObjectGenerator.deposit(origin["account_key"], 900000)

        status, _response = transfer(origin["account_key"], destination["account_key"], SILVER_DAILY_LIMIT)
        assert status == 201

    def test_gold_has_no_daily_limit(self):
        origin = ObjectGenerator.create_funded_account(1000000)
        destination = ObjectGenerator.create_account()

        status, _response = transfer(origin["account_key"], destination["account_key"], 300000)
        assert status == 201

        status, _response = transfer(origin["account_key"], destination["account_key"], 300000)
        assert status == 201
