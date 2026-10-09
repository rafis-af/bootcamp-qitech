from typing import Optional

from sqlalchemy import func, or_

from database import Context
from models import Fee, Level, Status, TransactionType


class CatalogRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_status(self, enumerator: str) -> Status:
        return self.session.query(Status).filter(Status.enumerator == enumerator).one()

    def get_level(self, enumerator: str) -> Level:
        return self.session.query(Level).filter(Level.enumerator == enumerator).one()

    def get_transaction_type(self, enumerator: str) -> TransactionType:
        return self.session.query(TransactionType).filter(TransactionType.enumerator == enumerator).one()

    def get_current_fee(self, level: Level, transaction_type: TransactionType) -> Optional[Fee]:
        return (
            self.session.query(Fee)
            .filter(
                Fee.level_id == level.id,
                Fee.transaction_type_id == transaction_type.id,
                Fee.starts_at <= func.now(),
                or_(Fee.ends_at.is_(None), Fee.ends_at > func.now()),
            )
            .order_by(Fee.starts_at.desc())
            .first()
        )
