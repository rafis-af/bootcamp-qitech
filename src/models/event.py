from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from models.base import Base
from models import Account, Client, Transaction


class Event(Base):
    __tablename__ = "event"

    id = Column(Integer, primary_key=True)
    event_key = Column(CHAR(36), nullable=False)
    event_type = Column(String(50), nullable=False)
    severity = Column(String(10), nullable=False)
    client_id = Column(Integer, ForeignKey(Client.id), nullable=True)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=True)
    transaction_id = Column(Integer, ForeignKey(Transaction.id), nullable=True)
    request_id = Column(String(64), nullable=True)
    detail = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("event_key"),)

    client = relationship("Client", foreign_keys=[client_id])
    account = relationship("Account", foreign_keys=[account_id])
    transaction = relationship("Transaction", foreign_keys=[transaction_id])

    CLIENT_REGISTERED = "client_registered"
    CLIENT_BLOCKED = "client_blocked"
    ACCOUNT_OPENED = "account_opened"
    ACCOUNT_BLOCKED = "account_blocked"
    ACCOUNT_UNBLOCKED = "account_unblocked"
    PASSWORD_FAILED = "password_failed"
    INCOME_ALERT = "income_alert"
    OPERATION_REFUSED = "operation_refused"

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

    REASON_MANUAL = "manual"
    REASON_PASSWORD = "password"
    REASON_INCOME = "income"
