from uuid import uuid4

from tests.utils import ObjectGenerator, PayloadGenerator, RequestGenerator

FEE = 150


class TestStatement:
    """Consultar extrato (RFC 5.9)."""

    def test_most_recent_first_with_signed_amounts_and_balance_after(self):
        origin = ObjectGenerator.create_funded_account(100000)
        destination = ObjectGenerator.create_account()

        payload = PayloadGenerator.create_transfer_payload(destination["account_key"], 10000)
        status, transfer = RequestGenerator.POST_transfer(origin["account_key"], payload)
        assert status == 201

        status, response = RequestGenerator.GET_statement(origin["account_key"])
        assert status == 200

        entries = [(entry["entry_type"], entry["amount"], entry["balance_after"]) for entry in response["data"]]
        assert entries == [
            ("fee", -FEE, 100000 - 10000 - FEE),
            ("transfer_out", -10000, 100000 - 10000),
            ("deposit", 100000, 100000),
        ]

        assert response["data"][0]["transaction_key"] == transfer["transaction_key"]
        assert response["data"][1]["transaction_key"] == transfer["transaction_key"]
        assert response["data"][0]["transaction_type"] == "transfer"

        ObjectGenerator.assert_balance_matches_statement(origin["account_key"])

    def test_pages(self):
        account = ObjectGenerator.create_account()
        for _deposit in range(3):
            ObjectGenerator.deposit(account["account_key"], 1000)

        status, response = RequestGenerator.GET_statement(account["account_key"], {"limit": 2})
        assert len(response["data"]) == 2
        assert response["is_last_page"] is False

        status, response = RequestGenerator.GET_statement(account["account_key"], {"limit": 2, "page": 1})
        assert len(response["data"]) == 1
        assert response["is_last_page"] is True
        assert response["limit"] == 2
        assert response["page"] == 1

    def test_period_filter(self):
        account = ObjectGenerator.create_funded_account(1000)

        status, response = RequestGenerator.GET_statement(
            account["account_key"], {"date_from": "2000-01-01", "date_to": "2000-12-31"}
        )
        assert status == 200
        assert response["data"] == []

        status, response = RequestGenerator.GET_statement(
            account["account_key"], {"date_from": "2000-01-01", "date_to": "2999-12-31"}
        )
        assert len(response["data"]) == 1

    def test_refuses_bad_filters(self):
        account = ObjectGenerator.create_account()

        status, response = RequestGenerator.GET_statement(
            account["account_key"], {"date_from": "2026-02-01", "date_to": "2026-01-01"}
        )
        assert status == 400
        assert response["code"] == "QIT000010"

        status, response = RequestGenerator.GET_statement(account["account_key"], {"date_from": "2026-02-30"})
        assert status == 422
        assert response["code"] == "QIT001006"

        for params in [{"limit": 101}, {"limit": 0}, {"date_from": "01/01/2026"}, {"desde": "2026-01-01"}]:
            status, response = RequestGenerator.GET_statement(account["account_key"], params)
            assert status == 400, params

    def test_unknown_account(self):
        status, response = RequestGenerator.GET_statement(str(uuid4()))

        assert status == 404
        assert response["code"] == "QIT001010"

    def test_last_day_of_the_calendar_is_accepted(self):
        """31/12/9999 é o último dia que existe: não pode estourar o cálculo do fim do período."""
        account = ObjectGenerator.create_account()

        status, response = RequestGenerator.GET_statement(account["account_key"], {"date_to": "9999-12-31"})

        assert status == 200
        assert response["data"] == []
