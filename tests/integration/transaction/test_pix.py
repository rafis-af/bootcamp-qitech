from uuid import uuid4

from tests.utils import ObjectGenerator, PayloadGenerator, RequestGenerator

FEE = 150


class TestPix:
    """Enviar Pix (RFC 5.8): o destino é achado pela chave; o resto é a transferência."""

    def test_sends_to_the_key_owner_and_returns_the_owner_name(self):
        origin = ObjectGenerator.create_funded_account(50000)
        destination = ObjectGenerator.create_account()
        pix_key = ObjectGenerator.create_pix_key(destination["account_key"], "email", destination["email"])

        payload = PayloadGenerator.create_pix_payload(pix_key["key_value"], 12000)
        status, response = RequestGenerator.POST_pix(origin["account_key"], payload)

        assert status == 201
        assert response["transaction_type"] == "pix"
        assert response["destination_account_key"] == destination["account_key"]
        assert response["destination_name"] == destination["name"]
        assert response["pix_key"] == {"key_type": "email", "key_value": destination["email"].lower()}
        assert response["fee"] == FEE

        assert ObjectGenerator.get_balance(origin["account_key"]) == 50000 - 12000 - FEE
        assert ObjectGenerator.get_balance(destination["account_key"]) == 12000

        entry_types = [entry["entry_type"] for entry in ObjectGenerator.get_full_statement(origin["account_key"])]
        assert entry_types[:2] == ["fee", "pix_out"]

        entry_types = [entry["entry_type"] for entry in ObjectGenerator.get_full_statement(destination["account_key"])]
        assert entry_types == ["pix_in"]

    def test_key_is_found_regardless_of_case(self):
        origin = ObjectGenerator.create_funded_account(50000)
        destination = ObjectGenerator.create_account()
        pix_key = ObjectGenerator.create_pix_key(destination["account_key"], "random")

        payload = PayloadGenerator.create_pix_payload(pix_key["key_value"].upper(), 100)
        status, response = RequestGenerator.POST_pix(origin["account_key"], payload)

        assert status == 201
        assert response["destination_account_key"] == destination["account_key"]

    def test_unknown_key(self):
        origin = ObjectGenerator.create_funded_account(50000)

        payload = PayloadGenerator.create_pix_payload(f"ninguem.{uuid4()}@exemplo.com.br", 100)
        status, response = RequestGenerator.POST_pix(origin["account_key"], payload)

        assert status == 404
        assert response["code"] == "QIT001030"

    def test_cannot_send_pix_to_its_own_key(self):
        origin = ObjectGenerator.create_funded_account(50000)
        pix_key = ObjectGenerator.create_pix_key(origin["account_key"], "random")

        payload = PayloadGenerator.create_pix_payload(pix_key["key_value"], 100)
        status, response = RequestGenerator.POST_pix(origin["account_key"], payload)

        assert status == 422
        assert response["code"] == "QIT001021"

    def test_same_refusals_as_the_transfer(self):
        origin = ObjectGenerator.create_funded_account(1000)
        destination = ObjectGenerator.create_account()
        pix_key = ObjectGenerator.create_pix_key(destination["account_key"], "random")

        payload = PayloadGenerator.create_pix_payload(pix_key["key_value"], 1000)
        status, response = RequestGenerator.POST_pix(origin["account_key"], payload)
        assert status == 422
        assert response["code"] == "QIT001022"

        payload = PayloadGenerator.create_pix_payload(pix_key["key_value"], 100, password="000000")
        status, response = RequestGenerator.POST_pix(origin["account_key"], payload)
        assert status == 401
        assert response["code"] == "QIT001013"
