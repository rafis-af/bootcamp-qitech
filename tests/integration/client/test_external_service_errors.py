from tests.utils import PayloadGenerator, RequestGenerator


def assert_nothing_was_saved(document_number: str) -> None:
    """Falha em Receita ou Serasa não grava cliente (RFC 5.1): a busca pelo CPF
    tem que voltar vazia."""
    status, response = RequestGenerator.GET_clients({"document_number": document_number})

    assert status == 200
    assert response["data"] == []


class TestExternalServiceErrors:
    """Cada jeito de a Receita ou a Serasa falhar tem o seu código (RFC 5.1).

    Os cenários vêm do mock, pelos três primeiros dígitos do CPF (mocks/app.py).
    """

    def test_receita_answers_with_an_http_error(self):
        payload = PayloadGenerator.create_client_payload(cpf_prefix="940")

        status, response = RequestGenerator.POST_client(payload)

        assert status == 502
        assert response["code"] == "QIT001041"
        assert "Receita" in response["translation"]
        assert_nothing_was_saved(payload["document_number"])

    def test_receita_answers_outside_the_agreed_format(self):
        payload = PayloadGenerator.create_client_payload(cpf_prefix="941")

        status, response = RequestGenerator.POST_client(payload)

        assert status == 502
        assert response["code"] == "QIT001042"
        assert "situation" in response["translation"]
        assert_nothing_was_saved(payload["document_number"])

    def test_receita_refuses_this_apis_credential(self):
        payload = PayloadGenerator.create_client_payload(cpf_prefix="942")

        status, response = RequestGenerator.POST_client(payload)

        assert status == 502
        assert response["code"] == "QIT001043"
        assert "recusou a credencial desta API" in response["translation"]
        assert_nothing_was_saved(payload["document_number"])

    def test_cpf_not_found_at_receita(self):
        payload = PayloadGenerator.create_client_payload(cpf_prefix="947")

        status, response = RequestGenerator.POST_client(payload)

        assert status == 422
        assert response["code"] == "QIT001044"
        assert response["field"] == "document_number"
        assert_nothing_was_saved(payload["document_number"])

    def test_serasa_answers_with_an_http_error(self):
        payload = PayloadGenerator.create_client_payload(cpf_prefix="950")

        status, response = RequestGenerator.POST_client(payload)

        assert status == 502
        assert response["code"] == "QIT001041"
        assert "Serasa" in response["translation"]
        assert_nothing_was_saved(payload["document_number"])

    def test_serasa_answer_without_the_score(self):
        payload = PayloadGenerator.create_client_payload(cpf_prefix="951")

        status, response = RequestGenerator.POST_client(payload)

        assert status == 502
        assert response["code"] == "QIT001042"
        assert "score" in response["translation"]
        assert_nothing_was_saved(payload["document_number"])
