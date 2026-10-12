from tests.utils import ObjectGenerator, PayloadGenerator, RequestGenerator


class TestKeyNormalization:
    """Chave de conta é UUID: maiúscula ou minúscula, é a mesma conta."""

    def test_destination_key_in_uppercase(self):
        origin = ObjectGenerator.create_funded_account(10000)
        destination = ObjectGenerator.create_account()

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"].upper(), 100)
        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)

        assert status == 201, response
        assert response["destination_account_key"] == destination["account_key"]

    def test_replay_with_the_origin_key_in_uppercase_is_still_a_replay(self):
        origin = ObjectGenerator.create_funded_account(10000)
        destination = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 100)

        status, first = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 201

        status, replay = RequestGenerator.POST_transfer(origin["account_key"].upper(), payload)

        assert status == 200, replay
        assert replay["transaction_key"] == first["transaction_key"]
        assert ObjectGenerator.get_balance(origin["account_key"]) == 10000 - 100 - first["fee"]
