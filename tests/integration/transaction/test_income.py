from tests.utils import DbUtils, ObjectGenerator, PayloadGenerator, RequestGenerator

# Renda de R$ 100,00: a verificação alerta acima de 2× = R$ 200,00 por saída.
MONTHLY_INCOME = 10000
INCOME_LIMIT = 2 * MONTHLY_INCOME


def transfer(origin_key: str, destination_key: str, amount: int) -> tuple:
    payload = PayloadGenerator.create_transfer_payload(destination_key, amount)
    return RequestGenerator.POST_transfer(origin_key, payload)


class TestIncome:
    """Verificar a renda (RFC 5.6): alertar sempre, bloquear só na repetição.

    Os testes usam cliente Ouro, que não tem limite diário: assim é só a
    regra de renda que está sendo testada.
    """

    def test_exactly_twice_the_income_is_not_an_alert(self):
        origin = ObjectGenerator.create_funded_account(1000000, monthly_income=MONTHLY_INCOME)
        destination = ObjectGenerator.create_account()

        status, response = transfer(origin["account_key"], destination["account_key"], INCOME_LIMIT)

        assert status == 201
        assert response["above_income"] is False

    def test_three_alerts_pass_and_the_fourth_is_refused_and_blocks(self):
        origin = ObjectGenerator.create_funded_account(1000000, monthly_income=MONTHLY_INCOME)
        destination = ObjectGenerator.create_account()

        for _alert in range(3):
            status, response = transfer(origin["account_key"], destination["account_key"], INCOME_LIMIT + 1)
            assert status == 201
            assert response["above_income"] is True

        balance_before = ObjectGenerator.get_balance(origin["account_key"])

        status, response = transfer(origin["account_key"], destination["account_key"], INCOME_LIMIT + 1)
        assert status == 422
        assert response["code"] == "QIT001024"

        assert ObjectGenerator.get_account(origin["account_key"])["status"] == "blocked"
        assert ObjectGenerator.get_balance(origin["account_key"]) == balance_before

        events = DbUtils.events_of_account(origin["account_key"])
        event_types = [event["event_type"] for event in events]
        assert event_types.count("income_alert") == 3
        assert "account_blocked" in event_types

        blocked_event = [event for event in events if event["event_type"] == "account_blocked"][0]
        assert blocked_event["detail"]["reason"] == "income"

    def test_outflows_within_the_income_do_not_use_the_quota(self):
        origin = ObjectGenerator.create_funded_account(1000000, monthly_income=MONTHLY_INCOME)
        destination = ObjectGenerator.create_account()

        for _transfer in range(5):
            status, response = transfer(origin["account_key"], destination["account_key"], INCOME_LIMIT)
            assert status == 201
            assert response["above_income"] is False

        status, response = transfer(origin["account_key"], destination["account_key"], INCOME_LIMIT + 1)
        assert status == 201
        assert response["above_income"] is True

    def test_quota_stays_used_after_unblock_in_the_same_month(self):
        """Desbloquear não devolve a cota do mês: a próxima saída acima da renda bloqueia de novo.

        Saída DENTRO da renda continua passando — o cliente não fica preso,
        só não pode repetir o que levou ao bloqueio até o mês virar.
        """
        origin = ObjectGenerator.create_funded_account(1000000, monthly_income=MONTHLY_INCOME)
        destination = ObjectGenerator.create_account()

        for _alert in range(4):
            transfer(origin["account_key"], destination["account_key"], INCOME_LIMIT + 1)

        RequestGenerator.PUT_account_status(origin["account_key"], PayloadGenerator.create_status_payload("active"))

        status, _response = transfer(origin["account_key"], destination["account_key"], 100)
        assert status == 201

        status, response = transfer(origin["account_key"], destination["account_key"], INCOME_LIMIT + 1)
        assert status == 422
        assert response["code"] == "QIT001024"
