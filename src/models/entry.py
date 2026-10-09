from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Account, Transaction


class Entry(Base):
    __tablename__ = "entry"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(Integer, ForeignKey(Transaction.id), nullable=False)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    entry_type = Column(String(20), nullable=False)
    amount = Column(BigInteger, nullable=False)
    balance_after = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    transaction = relationship(
        "Transaction",
        foreign_keys=[transaction_id],
        back_populates="entries",
        lazy="selectin",
    )
    account = relationship("Account", foreign_keys=[account_id])

    DEPOSIT = "deposit"
    TRANSFER_OUT = "transfer_out"
    TRANSFER_IN = "transfer_in"
    PIX_OUT = "pix_out"
    PIX_IN = "pix_in"
    FEE = "fee"
