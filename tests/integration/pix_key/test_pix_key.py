from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from tests.utils import DbUtils, ObjectGenerator, PayloadGenerator, RandomGenerator, RequestGenerator


def register(account_key: str, key_type: str, key_value: str = None, password: str = "123456") -> tuple:
    payload = PayloadGenerator.create_pix_key_payload(key_type, key_value, password=password)
    return RequestGenerator.POST_pix_key(account_key, payload)


def refusals_with_code(account_key: str, code: str) -> list:
    return [
        event for event in DbUtils.events_of_account(account_key)
        if event["event_type"] == "operation_refused" and event["detail"]["code"] == code
    ]


class TestPixKey:
    """Cadastrar chave Pix (RFC 5.7)."""

    def test_registers_each_key_type(self):
        account = ObjectGenerator.create_account()
        account_key = account["account_key"]

        status, random_key = register(account_key, "random")
        assert status == 201
        assert random_key["key_type"] == "random"
        assert len(random_key["key_value"]) == 36

        status, cpf_key = register(account_key, "cpf", account["document_number"])
        assert status == 201

        status, email_key = register(account_key, "email", account["email"].upper())
        assert status == 201
        assert email_key["key_value"] == account["email"].lower()

        status, phone_key = register(account_key, "phone", RandomGenerator.generate_phone())
        assert status == 201

        status, response = RequestGenerator.GET_pix_keys(account_key)
        assert status == 200
        assert [key["key_type"] for key in response["data"]] == ["random", "cpf", "email", "phone"]

    def test_cpf_key_must_be_the_owners(self):
        account = ObjectGenerator.create_account()

        status, response = register(account["account_key"], "cpf", RandomGenerator.generate_cpf())

        assert status == 422
        assert response["code"] == "QIT001032"

    def test_a_key_points_to_one_account_only(self):
        first = ObjectGenerator.create_account()
        second = ObjectGenerator.create_account()
        email = f"compartilhado.{uuid4()}@exemplo.com.br"

        status, _response = register(first["account_key"], "email", email)
        assert status == 201

        status, response = register(second["account_key"], "email", email.upper())
        assert status == 409
        assert response["code"] == "QIT001031"

    def test_two_accounts_registering_the_same_key_at_the_same_time(self):
        """Ao mesmo tempo, as duas passam pelo "já existe?" — e o UNIQUE barra a segunda."""
        accounts = [ObjectGenerator.create_account() for _account in range(2)]
        email = f"corrida.{uuid4()}@exemplo.com.br"

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda account: register(account["account_key"], "email", email), accounts))

        statuses = sorted(status for status, _response in results)
        assert statuses == [201, 409]

    def test_at_most_5_keys_per_account(self):
        account = ObjectGenerator.create_account()

        for _key in range(5):
            status, _response = register(account["account_key"], "random")
            assert status == 201

        status, response = register(account["account_key"], "random")
        assert status == 422
        assert response["code"] == "QIT001033"

        refusals = refusals_with_code(account["account_key"], "QIT001033")
        assert len(refusals) == 1
        assert refusals[0]["detail"]["operation"] == "create_pix_key"
        assert refusals[0]["request_id"] is not None

    def test_key_taken_by_another_account_becomes_an_event_without_the_key_value(self):
        first = ObjectGenerator.create_account()
        second = ObjectGenerator.create_account()
        email = f"evento.{uuid4()}@exemplo.com.br"
        register(first["account_key"], "email", email)

        status, response = register(second["account_key"], "email", email)
        assert status == 409
        assert response["code"] == "QIT001031"

        refusals = refusals_with_code(second["account_key"], "QIT001031")
        assert len(refusals) == 1
        # A chave é dado pessoal: o evento guarda o tipo, nunca o valor.
        assert email not in str(refusals[0]["detail"])

    def test_same_key_twice_in_the_same_account_becomes_an_event(self):
        account = ObjectGenerator.create_account()
        email = f"repetida.{uuid4()}@exemplo.com.br"
        register(account["account_key"], "email", email)

        status, response = register(account["account_key"], "email", email)
        assert status == 409
        assert response["code"] == "QIT001035"

        assert len(refusals_with_code(account["account_key"], "QIT001035")) == 1

    def test_asks_for_the_password(self):
        account = ObjectGenerator.create_account()

        status, response = register(account["account_key"], "random", password="000000")
        assert status == 401
        assert response["code"] == "QIT001013"

        status, response = RequestGenerator.GET_pix_keys(account["account_key"])
        assert response["data"] == []

    def test_blocked_account_does_not_register_keys(self):
        account = ObjectGenerator.create_account()
        RequestGenerator.PUT_account_status(account["account_key"], PayloadGenerator.create_status_payload("blocked"))

        status, response = register(account["account_key"], "random")

        assert status == 409
        assert response["code"] == "QIT001012"

    def test_schema_by_key_type(self):
        """O tipo decide o formato: random não leva valor; os outros levam, cada um com o seu."""
        account = ObjectGenerator.create_account()

        malformed = [
            ("random", "um-valor-que-nao-devia-vir"),
            ("email", None),
            ("email", "isto-nao-e-email"),
            ("phone", "11999999999"),
            ("cpf", "12345678901"),
            ("boleto", "qualquer"),
        ]

        for key_type, key_value in malformed:
            status, response = register(account["account_key"], key_type, key_value)

            assert status == 400, (key_type, key_value)
            assert response["code"] == "QIT000001"

    def test_unknown_account(self):
        status, response = register(str(uuid4()), "random")
        assert status == 404

        status, response = RequestGenerator.GET_pix_keys(str(uuid4()))
        assert status == 404
