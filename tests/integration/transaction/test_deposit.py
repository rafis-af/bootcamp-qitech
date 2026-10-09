from uuid import uuid4

from tests.utils import ObjectGenerator, PayloadGenerator, RequestGenerator


class TestDeposit:
    """Depositar (RFC 5.4): sem origem, sem tarifa, sem senha."""

    def test_cash_deposit(self):
        account = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_deposit_payload(150000)

        status, response = RequestGenerator.POST_deposit(account["account_key"], payload)

        assert status == 201
        assert response["transaction_key"] == payload["transaction_key"]
        assert response["transaction_type"] == "deposit"
        assert response["origin_account_key"] is None
        assert response["destination_account_key"] == account["account_key"]
        assert response["amount"] == 150000
        assert response["fee"] == 0
        assert response["deposit"]["method"] == "cash"
        assert response["deposit"]["source_bank_code"] is None

        assert ObjectGenerator.get_balance(account["account_key"]) == 150000
        ObjectGenerator.assert_balance_matches_statement(account["account_key"])

    def test_ted_deposit_requires_the_source_bank(self):
        account = ObjectGenerator.create_account()

        payload = PayloadGenerator.create_deposit_payload(1000, method="ted", source_bank_code="341")
        status, response = RequestGenerator.POST_deposit(account["account_key"], payload)
        assert status == 201
        assert response["deposit"]["source_bank_code"] == "341"

        payload = PayloadGenerator.create_deposit_payload(1000, method="ted")
        status, response = RequestGenerator.POST_deposit(account["account_key"], payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_cash_deposit_has_no_source_bank(self):
        account = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_deposit_payload(1000, method="cash", source_bank_code="341")

        status, response = RequestGenerator.POST_deposit(account["account_key"], payload)

        assert status == 400
        assert response["code"] == "QIT000001"

    def test_amount_goes_from_1_cent_to_1_million(self):
        account = ObjectGenerator.create_account()

        for valid_amount in [1, 100000000]:
            payload = PayloadGenerator.create_deposit_payload(valid_amount)
            status, _response = RequestGenerator.POST_deposit(account["account_key"], payload)
            assert status == 201, valid_amount

        for invalid_amount in [0, -100, 100000001, 10.5, "100"]:
            payload = PayloadGenerator.create_deposit_payload(1)
            payload["amount"] = invalid_amount
            status, response = RequestGenerator.POST_deposit(account["account_key"], payload)
            assert status == 400, invalid_amount
            assert response["code"] == "QIT000001"

    def test_refuses_invalid_depositor_cpf(self):
        account = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_deposit_payload(1000, depositor_document_number="111.222.333-44")

        status, response = RequestGenerator.POST_deposit(account["account_key"], payload)

        assert status == 422
        assert response["code"] == "QIT001002"

    def test_deposit_does_not_ask_for_password(self):
        """Qualquer um pode depositar numa conta: o contrato nem aceita o campo."""
        account = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_deposit_payload(1000)
        payload["password"] = "123456"

        status, response = RequestGenerator.POST_deposit(account["account_key"], payload)

        assert status == 400

    def test_unknown_account(self):
        status, response = RequestGenerator.POST_deposit(str(uuid4()), PayloadGenerator.create_deposit_payload(1000))

        assert status == 404
        assert response["code"] == "QIT001010"
