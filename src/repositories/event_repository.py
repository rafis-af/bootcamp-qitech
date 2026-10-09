from typing import Optional
from uuid import uuid4

from database import Context
from models import Account, Client, Event, Transaction
from utils.request_context import get_request_id


class EventRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(
        self,
        event_type: str,
        severity: str,
        client: Optional[Client] = None,
        account: Optional[Account] = None,
        transaction: Optional[Transaction] = None,
        detail: Optional[dict] = None,
    ) -> Event:
        if detail is None:
            detail = {}

        event = Event()

        event.event_key = str(uuid4())
        event.event_type = event_type
        event.severity = severity
        event.client = client
        event.account = account
        event.transaction = transaction
        event.request_id = get_request_id()
        event.detail = detail

        self.session.add(event)
        return event
