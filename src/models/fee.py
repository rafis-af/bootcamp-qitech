from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, Integer, func, text
from sqlalchemy.orm import relationship
from models.base import Base
from models import Level, TransactionType


class Fee(Base):
    __tablename__ = "fee"

    id = Column(Integer, primary_key=True)
    level_id = Column(Integer, ForeignKey(Level.id), nullable=False)
    transaction_type_id = Column(Integer, ForeignKey(TransactionType.id), nullable=False)
    amount = Column(BigInteger, nullable=False)
    starts_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    ends_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index(
            "fee_one_current_per_level_and_type",
            "level_id",
            "transaction_type_id",
            unique=True,
            postgresql_where=text("ends_at IS NULL"),
        ),
    )

    level = relationship("Level", foreign_keys=[level_id], lazy="selectin")
    transaction_type = relationship("TransactionType", foreign_keys=[transaction_type_id], lazy="selectin")
