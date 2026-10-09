from sqlalchemy import BigInteger, Boolean, CHAR, Column, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Account, Fee, PixKey, TransactionType


class Transaction(Base):
    __tablename__ = "transaction"

    id = Column(Integer, primary_key=True)
    transaction_key = Column(CHAR(36), nullable=False)
    transaction_type_id = Column(Integer, ForeignKey(TransactionType.id), nullable=False)
    origin_account_id = Column(Integer, ForeignKey(Account.id), nullable=True)
    destination_account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    pix_key_id = Column(Integer, ForeignKey(PixKey.id), nullable=True)
    amount = Column(BigInteger, nullable=False)
    fee_id = Column(Integer, ForeignKey(Fee.id), nullable=True)
    fee = Column(BigInteger, nullable=False)
    above_income = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("transaction_key"),)

    transaction_type = relationship("TransactionType", foreign_keys=[transaction_type_id], lazy="selectin")
    origin_account = relationship("Account", foreign_keys=[origin_account_id])
    destination_account = relationship("Account", foreign_keys=[destination_account_id])
    pix_key = relationship("PixKey", foreign_keys=[pix_key_id])
    applied_fee = relationship("Fee", foreign_keys=[fee_id])
    deposit = relationship("Deposit", back_populates="transaction", uselist=False)
    entries = relationship("Entry", back_populates="transaction", order_by="asc(Entry.id)")
