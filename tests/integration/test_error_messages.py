from uuid import uuid4

from tests.utils import INTERNAL_TOKEN, MockScenario, ObjectGenerator, PayloadGenerator, RequestGenerator
from tests.utils.requisition import ClientRequisition


def send_raw(method: str, endpoint: str, body: str = None, token: str = INTERNAL_TOKEN) -> tuple:
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["INTERNAL-TOKEN"] = token

    response = ClientRequisition.send(method, endpoint, headers=headers, data=body)
    return response.response_status, response.response_json, response.response


class TestBodyErrors:
    """O corpo que nem chega a ser validado pelo schema: cada problema tem o seu código."""

    def test_body_that_is_not_json(self):
        status, response, _raw = send_raw("POST", "/client", '{"name": "Ana",')

        assert status == 400
        assert response["code"] == "QIT000003"
        assert "JSON válido" in response["translation"]

    def test_missing_body(self):
        status, response, _raw = send_raw("POST", "/client")

        assert status == 400
        assert response["code"] == "QIT000004"

    def test_body_that_is_a_list(self):
        status, response, _raw = send_raw("POST", "/client", "[1, 2, 3]")

        assert status == 400
        assert response["code"] == "QIT000005"


class TestFieldMessages:
    """Erro de schema diz QUAL campo e COMO ele deveria vir, em português."""

    def test_missing_field_is_named(self):
        payload = PayloadGenerator.create_client_payload()
        del payload["email"]

        status, response = RequestGenerator.POST_client(payload)

        assert status == 400
        assert response["code"] == "QIT000001"
        assert response["field"] == "email"
        assert "'email' é obrigatório" in response["translation"]

    def test_unknown_field_lists_the_accepted_ones(self):
        payload = PayloadGenerator.create_client_payload()
        payload["apelido"] = "Mari"

        status, response = RequestGenerator.POST_client(payload)

        assert status == 400
        assert response["field"] == "apelido"
        assert "document_number" in response["translation"]

    def test_cpf_format_is_explained(self):
        payload = PayloadGenerator.create_client_payload(document_number="12345678900")

        status, response = RequestGenerator.POST_client(payload)

        assert status == 400
        assert response["field"] == "document_number"
        assert "000.000.000-00" in response["translation"]

    def test_money_must_be_integer_cents(self):
        account = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_deposit_payload(1000)
        payload["amount"] = 10.5

        status, response = RequestGenerator.POST_deposit(account["account_key"], payload)

        assert status == 400
        assert response["field"] == "amount"
        assert "centavos" in response["translation"]

    def test_income_must_be_positive(self):
        payload = PayloadGenerator.create_client_payload(monthly_income=0)

        status, response = RequestGenerator.POST_client(payload)

        assert status == 400
        assert response["field"] == "monthly_income"
        assert "maior que zero" in response["translation"]

    def test_wrong_password_format_never_echoes_the_value(self):
        client = ObjectGenerator.create_client()
        typed_password = "98ab76"

        status, response = RequestGenerator.POST_account(client["client_key"], {"password": typed_password})

        assert status == 400
        assert response["field"] == "password"
        assert "6 dígitos" in response["translation"]
        assert typed_password not in response["translation"]
        assert typed_password not in response["description"]

    def test_ted_without_bank_and_cash_with_bank(self):
        account = ObjectGenerator.create_account()

        payload = PayloadGenerator.create_deposit_payload(1000, method="ted")
        status, response = RequestGenerator.POST_deposit(account["account_key"], payload)
        assert status == 400
        assert response["field"] == "source_bank_code"
        assert "TED precisa" in response["translation"]

        payload = PayloadGenerator.create_deposit_payload(1000, method="cash", source_bank_code="341")
        status, response = RequestGenerator.POST_deposit(account["account_key"], payload)
        assert status == 400
        assert response["field"] == "source_bank_code"
        assert "espécie" in response["translation"]

    def test_random_key_must_not_bring_a_value(self):
        account = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_pix_key_payload("random", key_value="minha-chave")

        status, response = RequestGenerator.POST_pix_key(account["account_key"], payload)

        assert status == 400
        assert response["field"] == "key_value"
        assert "random" in response["translation"]

    def test_phone_key_format_is_explained(self):
        account = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_pix_key_payload("phone", key_value="11987654321")

        status, response = RequestGenerator.POST_pix_key(account["account_key"], payload)

        assert status == 400
        assert "+55" in response["translation"]

    def test_query_parameter_messages(self):
        account = ObjectGenerator.create_account()

        status, response = RequestGenerator.GET_statement(account["account_key"], {"limit": "0"})
        assert status == 400
        assert response["field"] == "limit"
        assert "parâmetro 'limit'" in response["translation"]

        status, response = RequestGenerator.GET_statement(account["account_key"], {"pagina": "1"})
        assert status == 400
        assert response["field"] == "pagina"

        status, response = RequestGenerator.GET_statement(
            account["account_key"], {"date_from": "2026-05-10", "date_to": "2026-05-01"}
        )
        assert status == 400
        assert response["code"] == "QIT000010"
        assert "invertido" in response["translation"]


class TestTokenAndRoutes:
    def test_missing_and_wrong_token_have_different_messages(self):
        status, missing, _raw = send_raw("GET", f"/account/{uuid4()}", token=None)
        assert status == 403

        status, wrong, _raw = send_raw("GET", f"/account/{uuid4()}", token="nao-e-o-token")
        assert status == 403

        assert missing["code"] == wrong["code"] == "QIT000002"
        assert "falta o header" in missing["translation"]
        assert "errado" in wrong["translation"]

    def test_unknown_route_and_wrong_method_are_named(self):
        status, response, raw = send_raw("GET", "/contas")
        assert status == 404
        assert "GET /contas" in response["translation"]
        assert raw.headers.get("X-Request-ID")

        status, response, _raw = send_raw("DELETE", f"/account/{uuid4()}")
        assert status == 405
        assert "GET" in response["translation"]


class TestBusinessMessages:
    def test_birthdate_in_the_future_and_implausible(self):
        status, response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(birthdate="2099-01-01"))
        assert status == 422
        assert response["code"] == "QIT001050"

        status, response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(birthdate="1850-01-01"))
        assert status == 422
        assert response["code"] == "QIT001051"

    def test_invalid_depositor_cpf_names_the_field(self):
        account = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_deposit_payload(1000, depositor_document_number="111.222.333-44")

        status, response = RequestGenerator.POST_deposit(account["account_key"], payload)

        assert status == 422
        assert response["code"] == "QIT001002"
        assert response["field"] == "depositor_document_number"
        assert "quem depositou" in response["translation"]

    def test_insufficient_balance_shows_the_values(self):
        origin = ObjectGenerator.create_funded_account(1000)
        destination = ObjectGenerator.create_account()

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 5000)
        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)

        assert status == 422
        assert response["code"] == "QIT001022"
        assert "R$ 51,50" in response["translation"]
        assert "R$ 10,00" in response["translation"]

    def test_daily_limit_says_how_much_is_left(self):
        origin = ObjectGenerator.create_funded_account(500000, cpf_prefix=MockScenario.SILVER)
        destination = ObjectGenerator.create_account()

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 70000)
        status, _response = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 201

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 50000)
        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)

        assert status == 422
        assert response["code"] == "QIT001023"
        assert "ainda cabem R$ 300,00" in response["translation"]

    def test_wrong_password_counts_down_in_portuguese(self):
        origin = ObjectGenerator.create_funded_account(1000)
        destination = ObjectGenerator.create_account()

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 100, password="000000")
        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 401
        assert "Restam 2 tentativas" in response["translation"]

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 100, password="000000")
        status, response = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 401
        assert "Resta 1 tentativa" in response["translation"]

    def test_blocked_account_message_names_the_operation(self):
        account = ObjectGenerator.create_account()
        RequestGenerator.PUT_account_status(account["account_key"], PayloadGenerator.create_status_payload("blocked"))

        status, response = RequestGenerator.POST_deposit(account["account_key"], PayloadGenerator.create_deposit_payload(1000))

        assert status == 409
        assert response["code"] == "QIT001012"
        assert "depósitos" in response["translation"]

    def test_pix_key_already_in_the_same_account(self):
        account = ObjectGenerator.create_account()
        email = f"repetida.{uuid4()}@exemplo.com.br"
        ObjectGenerator.create_pix_key(account["account_key"], "email", email)

        status, response = RequestGenerator.POST_pix_key(
            account["account_key"], PayloadGenerator.create_pix_key_payload("email", email)
        )

        assert status == 409
        assert response["code"] == "QIT001035"

    def test_transaction_key_conflict_tells_what_used_it(self):
        account = ObjectGenerator.create_account()
        payload = PayloadGenerator.create_deposit_payload(1000)
        status, _response = RequestGenerator.POST_deposit(account["account_key"], payload)
        assert status == 201

        payload["amount"] = 2000
        status, response = RequestGenerator.POST_deposit(account["account_key"], payload)

        assert status == 409
        assert response["code"] == "QIT001020"
        assert "deposit de R$ 10,00" in response["translation"]
