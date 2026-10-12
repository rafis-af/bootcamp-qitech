from uuid import uuid4

from tests.utils import DbUtils, MockScenario, ObjectGenerator, PayloadGenerator, RequestGenerator


def refusals_with_code(client_key: str, code: str) -> list:
    return [
        event for event in DbUtils.events_of_client(client_key)
        if event["event_type"] == "operation_refused" and event["detail"]["code"] == code
    ]


class TestAccountOpen:
    def test_opens_with_zero_balance_and_never_returns_the_password(self):
        client = ObjectGenerator.create_client()

        status, response = RequestGenerator.POST_account(
            client["client_key"], PayloadGenerator.create_account_payload("482913")
        )

        assert status == 201
        assert response["balance"] == 0
        assert response["status"] == "active"
        assert response["level"] == "gold"
        assert response["client_key"] == client["client_key"]

        assert "482913" not in str(response)
        assert "password" not in str(response)

        status, response = RequestGenerator.GET_account(response["account_key"])
        assert status == 200
        assert "password" not in str(response)

    def test_one_account_per_client(self):
        account = ObjectGenerator.create_account()

        status, response = RequestGenerator.POST_account(
            account["client_key"], PayloadGenerator.create_account_payload()
        )

        assert status == 409
        assert response["code"] == "QIT001011"

    def test_blocked_client_never_opens_an_account(self):
        client = ObjectGenerator.create_client(MockScenario.SERASA_RESTRICTION)

        status, response = RequestGenerator.POST_account(
            client["client_key"], PayloadGenerator.create_account_payload()
        )

        assert status == 409
        assert response["code"] == "QIT001008"

        refusals = refusals_with_code(client["client_key"], "QIT001008")
        assert len(refusals) == 1
        assert refusals[0]["detail"]["operation"] == "open_account"
        assert refusals[0]["request_id"] is not None

    def test_second_account_refusal_becomes_an_event(self):
        account = ObjectGenerator.create_account()

        status, response = RequestGenerator.POST_account(
            account["client_key"], PayloadGenerator.create_account_payload()
        )
        assert status == 409
        assert response["code"] == "QIT001011"

        assert len(refusals_with_code(account["client_key"], "QIT001011")) == 1

    def test_unknown_client(self):
        status, response = RequestGenerator.POST_account(str(uuid4()), PayloadGenerator.create_account_payload())

        assert status == 404
        assert response["code"] == "QIT001001"

    def test_password_must_have_6_digits_and_is_never_echoed(self):
        client = ObjectGenerator.create_client()

        for wrong_password in ["12345", "1234567", "12a456", 123456]:
            status, response = RequestGenerator.POST_account(client["client_key"], {"password": wrong_password})

            assert status == 400, wrong_password
            assert response["code"] == "QIT000001"
            assert str(wrong_password) not in response["description"]

    def test_get_unknown_account(self):
        status, response = RequestGenerator.GET_account(str(uuid4()))

        assert status == 404
        assert response["code"] == "QIT001010"
