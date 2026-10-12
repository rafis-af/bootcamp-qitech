from uuid import uuid4

from tests.utils import DbUtils, ObjectGenerator, PayloadGenerator, RequestGenerator

FEE = 150


class TestTransfer:
    """Transferir (RFC 5.5): quem envia paga a tarifa, quem recebe ganha o valor cheio."""

    def test_moves_the_amount_and_charges_the_fee_from_the_sender(self):
        origin = ObjectGenerator.create_funded_account(100000)
        destination = ObjectGenerator.create_account()

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 25000)
        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)

        assert status == 201
        assert response["transaction_type"] == "transfer"
        assert response["origin_account_key"] == origin["account_key"]
        assert response["destination_account_key"] == destination["account_key"]
        assert response["amount"] == 25000
        assert response["fee"] == FEE
        assert response["above_income"] is False

        assert ObjectGenerator.get_balance(origin["account_key"]) == 100000 - 25000 - FEE
        assert ObjectGenerator.get_balance(destination["account_key"]) == 25000

        ObjectGenerator.assert_balance_matches_statement(origin["account_key"])
        ObjectGenerator.assert_balance_matches_statement(destination["account_key"])

    def test_balance_must_cover_amount_plus_fee(self):
        """Saldo exato (valor + tarifa) passa e zera a conta; um centavo a menos é recusado."""
        origin = ObjectGenerator.create_funded_account(10000 + FEE)
        destination = ObjectGenerator.create_account()

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 10001)
        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 422
        assert response["code"] == "QIT001022"
        assert ObjectGenerator.get_balance(origin["account_key"]) == 10000 + FEE

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 10000)
        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 201
        assert ObjectGenerator.get_balance(origin["account_key"]) == 0

    def test_insufficient_balance_becomes_an_event(self):
        origin = ObjectGenerator.create_funded_account(100)
        destination = ObjectGenerator.create_account()

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 5000)
        status, _response = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 422

        refusals = [
            event for event in DbUtils.events_of_account(origin["account_key"])
            if event["event_type"] == "operation_refused"
        ]
        assert len(refusals) == 1
        assert refusals[0]["detail"]["code"] == "QIT001022"
        assert refusals[0]["detail"]["transaction_key"] == payload["transaction_key"]
        assert refusals[0]["request_id"] is not None

    def test_cannot_transfer_to_itself(self):
        origin = ObjectGenerator.create_funded_account(10000)

        payload = PayloadGenerator.create_transfer_payload(origin["account_key"], 100)
        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)

        assert status == 422
        assert response["code"] == "QIT001021"

    def test_unknown_origin_or_destination(self):
        origin = ObjectGenerator.create_funded_account(10000)

        payload = PayloadGenerator.create_transfer_payload(str(uuid4()), 100)
        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 404
        assert response["code"] == "QIT001015"
        assert response["field"] == "destination_account_key"

        payload = PayloadGenerator.create_transfer_payload(origin["account_key"], 100)
        status, response = RequestGenerator.POST_transfer(str(uuid4()), payload)
        assert status == 404
        assert response["code"] == "QIT001010"

    def test_blocked_destination_does_not_receive(self):
        origin = ObjectGenerator.create_funded_account(10000)
        destination = ObjectGenerator.create_account()
        RequestGenerator.PUT_account_status(destination["account_key"], PayloadGenerator.create_status_payload("blocked"))

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 100)
        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)

        assert status == 409
        assert response["code"] == "QIT001016"
        assert ObjectGenerator.get_balance(origin["account_key"]) == 10000
        assert ObjectGenerator.get_balance(destination["account_key"]) == 0

    def test_blocked_origin_does_not_send(self):
        origin = ObjectGenerator.create_funded_account(10000)
        destination = ObjectGenerator.create_account()
        RequestGenerator.PUT_account_status(origin["account_key"], PayloadGenerator.create_status_payload("blocked"))

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 100)
        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)

        assert status == 409
        assert response["code"] == "QIT001012"

    def test_schema_refuses_malformed_transfer(self):
        origin = ObjectGenerator.create_funded_account(10000)
        destination = ObjectGenerator.create_account()

        malformed_fields = [
            ("transaction_key", "nao-e-um-uuid"),
            ("destination_account_key", "nao-e-um-uuid"),
            ("amount", 0),
            ("password", "12345"),
        ]

        for field, malformed_value in malformed_fields:
            payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 100)
            payload[field] = malformed_value

            status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)

            assert status == 400, field
            assert response["code"] == "QIT000001"

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 100)
        del payload["password"]
        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 400
