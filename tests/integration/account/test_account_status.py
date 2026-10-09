from uuid import uuid4

from tests.utils import DbUtils, ObjectGenerator, PayloadGenerator, RequestGenerator


class TestAccountStatus:
    
    def test_block_and_unblock(self):
        account = ObjectGenerator.create_account()
        account_key = account["account_key"]

        status, response = RequestGenerator.PUT_account_status(account_key, PayloadGenerator.create_status_payload("blocked"))
        assert status == 200
        assert response["status"] == "blocked"

        status, response = RequestGenerator.PUT_account_status(account_key, PayloadGenerator.create_status_payload("active"))
        assert status == 200
        assert response["status"] == "active"

        events = DbUtils.events_of_account(account_key)
        event_types = [event["event_type"] for event in events]
        assert event_types == ["account_opened", "account_blocked", "account_unblocked"]
        assert events[1]["detail"]["reason"] == "manual"
        assert events[1]["severity"] == "critical"

    def test_same_status_is_nothing_to_change(self):
        account = ObjectGenerator.create_account()

        status, response = RequestGenerator.PUT_account_status(
            account["account_key"], PayloadGenerator.create_status_payload("active")
        )

        assert status == 409
        assert response["code"] == "QIT001014"

    def test_blocked_account_does_not_deposit_and_the_refusal_is_an_event(self):
        account = ObjectGenerator.create_account()
        account_key = account["account_key"]
        RequestGenerator.PUT_account_status(account_key, PayloadGenerator.create_status_payload("blocked"))

        status, response = RequestGenerator.POST_deposit(account_key, PayloadGenerator.create_deposit_payload(1000))

        assert status == 409
        assert response["code"] == "QIT001012"
        assert ObjectGenerator.get_balance(account_key) == 0

        refusals = [event for event in DbUtils.events_of_account(account_key) if event["event_type"] == "operation_refused"]
        assert len(refusals) == 1
        assert refusals[0]["detail"]["code"] == "QIT001012"

    def test_invalid_status_and_unknown_account(self):
        account = ObjectGenerator.create_account()

        status, response = RequestGenerator.PUT_account_status(
            account["account_key"], PayloadGenerator.create_status_payload("frozen")
        )
        assert status == 400
        assert response["code"] == "QIT000001"

        status, response = RequestGenerator.PUT_account_status(str(uuid4()), PayloadGenerator.create_status_payload("blocked"))
        assert status == 404
        assert response["code"] == "QIT001010"
