from uuid import uuid4

from tests.utils import DbUtils, ObjectGenerator, PayloadGenerator, RequestGenerator

FEE = 150


class TestIdempotency:
    """O ID único da operação (RFC 2.2): repetir o pedido nunca move o dinheiro de novo."""

    def test_repeated_transfer_returns_the_original_and_moves_nothing(self):
        """O app travou e a pessoa tocou de novo: o segundo toque devolve a mesma transferência."""
        origin = ObjectGenerator.create_funded_account(100000)
        destination = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 10000)

        status, original = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 201

        status, repeated = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 200
        assert repeated == original

        assert ObjectGenerator.get_balance(origin["account_key"]) == 100000 - 10000 - FEE
        assert ObjectGenerator.get_balance(destination["account_key"]) == 10000

    def test_repeated_deposit_and_pix(self):
        account = ObjectGenerator.create_account()
        deposit_payload = PayloadGenerator.create_deposit_payload(50000)

        status, _response = RequestGenerator.POST_deposit(account["account_key"], deposit_payload)
        assert status == 201
        status, _response = RequestGenerator.POST_deposit(account["account_key"], deposit_payload)
        assert status == 200
        assert ObjectGenerator.get_balance(account["account_key"]) == 50000

        destination = ObjectGenerator.create_account()
        pix_key = ObjectGenerator.create_pix_key(destination["account_key"])
        pix_payload = PayloadGenerator.create_pix_payload(pix_key["key_value"], 1000)

        status, _response = RequestGenerator.POST_pix(account["account_key"], pix_payload)
        assert status == 201
        status, response = RequestGenerator.POST_pix(account["account_key"], pix_payload)
        assert status == 200
        assert response["destination_name"] == destination["name"]
        assert ObjectGenerator.get_balance(destination["account_key"]) == 1000

    def test_same_key_with_other_data_is_a_conflict(self):
        origin = ObjectGenerator.create_funded_account(100000)
        destination = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 10000)

        status, _response = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 201

        other_amount = dict(payload, amount=20000)
        status, response = RequestGenerator.POST_transfer(origin["account_key"], other_amount)
        assert status == 409
        assert response["code"] == "QIT001020"

        # O mesmo ID num depósito: outro TIPO de operação, também conflito.
        deposit_payload = PayloadGenerator.create_deposit_payload(10000, transaction_key=payload["transaction_key"])
        status, response = RequestGenerator.POST_deposit(destination["account_key"], deposit_payload)
        assert status == 409
        assert response["code"] == "QIT001020"

        assert ObjectGenerator.get_balance(origin["account_key"]) == 100000 - 10000 - FEE

        conflicts = [
            event for event in DbUtils.events_of_account(origin["account_key"])
            if event["event_type"] == "operation_refused" and event["detail"]["code"] == "QIT001020"
        ]
        assert len(conflicts) == 1

    def test_the_key_is_case_insensitive(self):
        origin = ObjectGenerator.create_funded_account(100000)
        destination = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 10000)

        status, _response = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 201

        status, _response = RequestGenerator.POST_transfer(
            origin["account_key"], dict(payload, transaction_key=payload["transaction_key"].upper())
        )
        assert status == 200

    def test_a_refused_operation_does_not_use_up_its_key(self):
        """Recusa não grava operação: o mesmo ID pode ser tentado de novo e passar."""
        origin = ObjectGenerator.create_funded_account(1000)
        destination = ObjectGenerator.create_account()
        transaction_key = str(uuid4())
        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 5000, transaction_key=transaction_key)

        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 422

        ObjectGenerator.deposit(origin["account_key"], 10000)

        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 201
        assert response["transaction_key"] == transaction_key
