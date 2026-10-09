from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Account


class PixKey(Base):
    __tablename__ = "pix_key"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    key_type = Column(String(10), nullable=False)
    key_value = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("key_value"),)

    account = relationship("Account", foreign_keys=[account_id], lazy="selectin")

    CPF = "cpf"
    EMAIL = "email"
    PHONE = "phone"
    RANDOM = "random"
