from uuid import uuid4

from tests.utils import DbUtils, MockScenario, ObjectGenerator, PayloadGenerator, RequestGenerator


def extract_keys(response: dict) -> list:
    return [client["client_key"] for client in response["data"]]


class TestClientGet:
    def test_get_shows_the_account_after_it_is_opened(self):
        client = ObjectGenerator.create_client()

        status, response = RequestGenerator.GET_client(client["client_key"])
        assert status == 200
        assert response["account_key"] is None

        status, account = RequestGenerator.POST_account(
            client["client_key"], PayloadGenerator.create_account_payload()
        )
        assert status == 201

        status, response = RequestGenerator.GET_client(client["client_key"])
        assert status == 200
        assert response["account_key"] == account["account_key"]

    def test_not_found(self):
        status, response = RequestGenerator.GET_client(str(uuid4()))

        assert status == 404
        assert response["code"] == "QIT001001"


class TestClientList:
    def test_pages(self):
        DbUtils.rollback()

        for _client in range(3):
            ObjectGenerator.create_client()

        status, response = RequestGenerator.GET_clients()
        assert status == 200
        assert len(response["data"]) == 3
        assert response["is_last_page"] is True

        status, response = RequestGenerator.GET_clients({"limit": 2})
        assert len(response["data"]) == 2
        assert response["is_last_page"] is False

        status, response = RequestGenerator.GET_clients({"limit": 2, "page": 1})
        assert len(response["data"]) == 1
        assert response["is_last_page"] is True

    def test_filters_by_level_and_status(self):
        DbUtils.rollback()

        gold = ObjectGenerator.create_client()
        silver = ObjectGenerator.create_client(MockScenario.SILVER)
        blocked = ObjectGenerator.create_client(MockScenario.SERASA_RESTRICTION)

        status, response = RequestGenerator.GET_clients({"level": "silver"})
        assert status == 200
        assert extract_keys(response) == [silver["client_key"]]

        status, response = RequestGenerator.GET_clients({"status": "blocked"})
        assert extract_keys(response) == [blocked["client_key"]]

        status, response = RequestGenerator.GET_clients({"level": ["silver", "gold"]})
        assert sorted(extract_keys(response)) == sorted([gold["client_key"], silver["client_key"]])

    def test_list_does_not_carry_the_account(self):
        """A lista traz o resumo; a conta só no GET de um cliente (uma consulta a menos por item)."""
        client = ObjectGenerator.create_client()

        status, response = RequestGenerator.GET_clients({"document_number": client["document_number"]})

        assert status == 200
        assert extract_keys(response) == [client["client_key"]]
        assert "account_key" not in response["data"][0]

    def test_refuses_unknown_and_malformed_params(self):
        # limit=0 devolveria uma página vazia com is_last_page false, pra
        # sempre: quem pagina "até a última" ficaria num laço infinito.
        for params in [{"stauts": "active"}, {"limit": 500}, {"limit": 0}, {"page": -1}, {"level": "platinum"}]:
            status, response = RequestGenerator.GET_clients(params)

            assert status == 400, params
            assert response["code"] == "QIT000001"
