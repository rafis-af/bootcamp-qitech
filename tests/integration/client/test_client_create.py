from datetime import date, datetime
from zoneinfo import ZoneInfo

from tests.utils import DbUtils, MockScenario, ObjectGenerator, PayloadGenerator, RequestGenerator


def birthdate_for_age(age_in_years: int) -> str:
    """A data de nascimento de quem faz essa idade hoje (com o recuo do 29/02).

    "Hoje" no calendário de São Paulo, o mesmo da API. O container dos
    testes roda em UTC: com date.today(), das 21h à meia-noite de Brasília
    o teste já estaria no dia seguinte, e quem faz 18 anos amanhã para a
    API passaria por quem faz 18 hoje.
    """
    today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

    if today.month == 2 and today.day == 29:
        return date(today.year - age_in_years, 2, 28).isoformat()

    return date(today.year - age_in_years, today.month, today.day).isoformat()


def find_by_document_number(document_number: str) -> list:
    status, response = RequestGenerator.GET_clients({"document_number": document_number})
    assert status == 200
    return response["data"]


class TestClientClassification:
    """Os desfechos do cadastro que GRAVAM o cliente (RFC 5.1)."""

    def test_clean_client_is_gold(self):
        payload = PayloadGenerator.create_client_payload()

        status, response = RequestGenerator.POST_client(payload)

        assert status == 201
        assert response["status"] == "active"
        assert response["level"] == "gold"
        assert response["name"] == payload["name"]
        assert response["document_number"] == payload["document_number"]
        assert response["monthly_income"] == payload["monthly_income"]
        assert response["account_key"] is None

        events = DbUtils.events_of_client(response["client_key"])
        assert [event["event_type"] for event in events] == ["client_registered"]
        assert events[0]["detail"]["score"] == 800

    def test_score_below_600_is_silver(self):
        response = ObjectGenerator.create_client(MockScenario.SERASA_SCORE_599)

        assert response["level"] == "silver"

    def test_score_exactly_600_is_gold(self):
        """A borda: "score ≥ 600" inclui o 600. Um > no lugar do >= deixaria este cliente Prata."""
        response = ObjectGenerator.create_client(MockScenario.SERASA_SCORE_600)

        assert response["level"] == "gold"

    def test_no_score_is_silver(self):
        response = ObjectGenerator.create_client(MockScenario.SERASA_NO_SCORE)

        assert response["level"] == "silver"

    def test_late_payments_make_a_good_score_silver(self):
        response = ObjectGenerator.create_client(MockScenario.SERASA_LATE_PAYMENTS)

        assert response["level"] == "silver"

    def test_restriction_is_saved_as_blocked_without_level(self):
        """Nome sujo NÃO é recusa: o cliente é gravado bloqueado, sem nível (201).

        E é justamente por estar gravado que o mesmo CPF não consegue
        tentar de novo (RFC 6.1).
        """
        response = ObjectGenerator.create_client(MockScenario.SERASA_RESTRICTION)

        assert response["status"] == "blocked"
        assert response["level"] is None

        events = DbUtils.events_of_client(response["client_key"])
        assert events[0]["event_type"] == "client_blocked"
        assert events[0]["detail"]["reason"] == "restriction"

        payload_again = PayloadGenerator.create_client_payload(document_number=response["document_number"])
        status, response = RequestGenerator.POST_client(payload_again)

        assert status == 409
        assert response["code"] == "QIT001003"

    def test_high_fraud_risk_is_saved_as_blocked(self):
        response = ObjectGenerator.create_client(MockScenario.SERASA_HIGH_FRAUD_RISK)

        assert response["status"] == "blocked"
        assert response["level"] is None


class TestClientRefusals:
    """Os desfechos que RECUSAM o cadastro — e não gravam nada."""

    def test_irregular_cpf_is_refused_and_nothing_is_saved(self):
        """Diferente do nome sujo: CPF irregular na Receita não vira cliente nenhum.

        A prova de que nada foi gravado é a segunda tentativa: ela leva o
        MESMO 422, e não um 409 de "já cadastrado".
        """
        payload = PayloadGenerator.create_client_payload(cpf_prefix=MockScenario.RECEITA_SUSPENDED)

        status, response = RequestGenerator.POST_client(payload)
        assert status == 422
        assert response["code"] == "QIT001007"
        assert find_by_document_number(payload["document_number"]) == []

        status, response = RequestGenerator.POST_client(payload)
        assert status == 422
        assert response["code"] == "QIT001007"

    def test_canceled_cpf_is_refused(self):
        payload = PayloadGenerator.create_client_payload(cpf_prefix=MockScenario.RECEITA_CANCELED)

        status, response = RequestGenerator.POST_client(payload)

        assert status == 422
        assert response["code"] == "QIT001007"

    def test_receita_without_answer_in_5_seconds_is_refused(self):
        """O mock demora 6 s; o connector desiste aos 5 s. Nada é gravado, e dá pra repetir."""
        payload = PayloadGenerator.create_client_payload(cpf_prefix=MockScenario.RECEITA_SLOW)

        status, response = RequestGenerator.POST_client(payload)

        assert status == 503
        assert response["code"] == "QIT001009"
        assert find_by_document_number(payload["document_number"]) == []

    def test_serasa_without_answer_in_5_seconds_is_refused(self):
        payload = PayloadGenerator.create_client_payload(cpf_prefix=MockScenario.SERASA_SLOW)

        status, response = RequestGenerator.POST_client(payload)

        assert status == 503
        assert response["code"] == "QIT001009"
        assert find_by_document_number(payload["document_number"]) == []

    def test_refuses_invalid_cpf(self):
        payload = PayloadGenerator.create_client_payload(document_number="111.222.333-44")

        status, response = RequestGenerator.POST_client(payload)

        assert status == 422
        assert response["code"] == "QIT001002"

    def test_refuses_duplicated_document_number(self):
        first = PayloadGenerator.create_client_payload()
        status, _response = RequestGenerator.POST_client(first)
        assert status == 201

        second = PayloadGenerator.create_client_payload(document_number=first["document_number"])
        status, response = RequestGenerator.POST_client(second)

        assert status == 409
        assert response["code"] == "QIT001003"

    def test_refuses_duplicated_email_ignoring_case(self):
        """"Maria@x.com" e "maria@x.com" são a mesma caixa de correio."""
        first = PayloadGenerator.create_client_payload()
        status, _response = RequestGenerator.POST_client(first)
        assert status == 201

        second = PayloadGenerator.create_client_payload(email=first["email"].upper())
        status, response = RequestGenerator.POST_client(second)

        assert status == 409
        assert response["code"] == "QIT001004"

    def test_refuses_underage_and_accepts_exactly_18(self):
        payload = PayloadGenerator.create_client_payload(birthdate=birthdate_for_age(17))
        status, response = RequestGenerator.POST_client(payload)
        assert status == 422
        assert response["code"] == "QIT001005"

        payload = PayloadGenerator.create_client_payload(birthdate=birthdate_for_age(18))
        status, response = RequestGenerator.POST_client(payload)
        assert status == 201

    def test_refuses_impossible_birthdate(self):
        for impossible_birthdate in ["9999-99-99", "2025-02-30"]:
            payload = PayloadGenerator.create_client_payload(birthdate=impossible_birthdate)

            status, response = RequestGenerator.POST_client(payload)

            assert status == 422
            assert response["code"] == "QIT001006"

    def test_schema_refuses_malformed_fields(self):
        """Formato é do schema (400), antes de qualquer regra ou consulta externa."""
        malformed_fields = [
            ("email", "isto-nao-e-um-email"),
            ("document_number", "12345678901"),
            ("birthdate", "17/05/1990"),
            ("monthly_income", -1),
            ("monthly_income", "5000"),
            ("name", "   "),
        ]

        for field, malformed_value in malformed_fields:
            payload = PayloadGenerator.create_client_payload()
            payload[field] = malformed_value

            status, response = RequestGenerator.POST_client(payload)

            assert status == 400, f"o campo '{field}' aceitou o valor '{malformed_value}'"
            assert response["code"] == "QIT000001"

    def test_schema_refuses_missing_and_unknown_fields(self):
        payload = PayloadGenerator.create_client_payload()
        del payload["monthly_income"]
        status, response = RequestGenerator.POST_client(payload)
        assert status == 400

        payload = PayloadGenerator.create_client_payload()
        payload["campo_que_nao_existe"] = 1
        status, response = RequestGenerator.POST_client(payload)
        assert status == 400
