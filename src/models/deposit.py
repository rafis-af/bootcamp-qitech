from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Transaction


class Deposit(Base):
    __tablename__ = "deposit"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey(Transaction.id), nullable=False)
    method = Column(String(10), nullable=False)
    depositor_name = Column(String(255), nullable=False)
    depositor_document_number = Column(CHAR(14), nullable=False)
    source_bank_code = Column(CHAR(3), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("transaction_id"),)

    transaction = relationship("Transaction", foreign_keys=[transaction_id], back_populates="deposit")

    CASH = "cash"
    TED = "ted"
