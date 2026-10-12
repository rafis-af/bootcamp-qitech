from tests.utils import DbUtils, ObjectGenerator, PayloadGenerator, RequestGenerator

WRONG_PASSWORD = "000000"


def transfer(origin_key: str, destination_key: str, amount: int, password: str) -> tuple:
    payload = PayloadGenerator.create_transfer_payload(destination_key, amount, password=password)
    return RequestGenerator.POST_transfer(origin_key, payload)


class TestPassword:

    def test_third_wrong_password_in_a_row_blocks_the_account(self):
        origin = ObjectGenerator.create_funded_account(10000)
        destination = ObjectGenerator.create_account()

        status, response = transfer(origin["account_key"], destination["account_key"], 100, WRONG_PASSWORD)
        assert status == 401
        assert response["code"] == "QIT001013"

        status, response = transfer(origin["account_key"], destination["account_key"], 100, WRONG_PASSWORD)
        assert status == 401

        status, response = transfer(origin["account_key"], destination["account_key"], 100, WRONG_PASSWORD)
        assert status == 423
        assert response["code"] == "QIT001017"
        assert response["field"] == "password"

        # Bloqueada, nem a senha certa passa.
        status, response = transfer(origin["account_key"], destination["account_key"], 100, "123456")
        assert status == 409
        assert response["code"] == "QIT001012"

        assert ObjectGenerator.get_account(origin["account_key"])["status"] == "blocked"
        assert ObjectGenerator.get_balance(origin["account_key"]) == 10000

        events = DbUtils.events_of_account(origin["account_key"])
        password_events = [event for event in events if event["event_type"] == "password_failed"]
        blocked_events = [event for event in events if event["event_type"] == "account_blocked"]
        assert len(password_events) == 3
        assert blocked_events[0]["detail"]["reason"] == "password"

    def test_unblock_resets_the_attempts(self):
        origin = ObjectGenerator.create_funded_account(10000)
        destination = ObjectGenerator.create_account()

        for _attempt in range(3):
            transfer(origin["account_key"], destination["account_key"], 100, WRONG_PASSWORD)

        status, _response = RequestGenerator.PUT_account_status(
            origin["account_key"], PayloadGenerator.create_status_payload("active")
        )
        assert status == 200

        # Se o desbloqueio não zerasse o contador, esta seria a 4ª errada e
        # bloquearia de novo. Zerado, é a 1ª.
        status, response = transfer(origin["account_key"], destination["account_key"], 100, WRONG_PASSWORD)
        assert status == 401
        assert "2" in response["translation"]

        status, _response = transfer(origin["account_key"], destination["account_key"], 100, "123456")
        assert status == 201

    def test_a_right_password_resets_the_counter(self):
        """"Seguidas" é a palavra que importa: um acerto no meio zera a conta."""
        origin = ObjectGenerator.create_funded_account(10000)
        destination = ObjectGenerator.create_account()

        for password in [WRONG_PASSWORD, WRONG_PASSWORD, "123456", WRONG_PASSWORD, WRONG_PASSWORD]:
            transfer(origin["account_key"], destination["account_key"], 100, password)

        assert ObjectGenerator.get_account(origin["account_key"])["status"] == "active"

    def test_a_right_password_resets_the_counter_even_if_the_operation_is_refused(self):
        """A senha estava certa e o saldo não dava: o acerto conta assim mesmo.

        A recusa por saldo vem DEPOIS da senha, e o commit dela leva junto
        o contador zerado. Sem isso, as duas erradas de antes continuariam
        valendo, e a próxima errada bloquearia a conta.
        """
        origin = ObjectGenerator.create_funded_account(100)
        destination = ObjectGenerator.create_account()

        transfer(origin["account_key"], destination["account_key"], 1, WRONG_PASSWORD)
        transfer(origin["account_key"], destination["account_key"], 1, WRONG_PASSWORD)

        status, response = transfer(origin["account_key"], destination["account_key"], 5000, "123456")
        assert status == 422
        assert response["code"] == "QIT001022"

        status, response = transfer(origin["account_key"], destination["account_key"], 1, WRONG_PASSWORD)
        assert status == 401
        assert ObjectGenerator.get_account(origin["account_key"])["status"] == "active"
