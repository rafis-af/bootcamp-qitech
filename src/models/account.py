from sqlalchemy import BigInteger, CHAR, Column, DateTime, ForeignKey, Integer, SmallInteger, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Client, Status


class Account(Base):
    __tablename__ = "account"

    id = Column(Integer, primary_key=True)
    account_key = Column(CHAR(36), nullable=False)
    client_id = Column(Integer, ForeignKey(Client.id), nullable=False)
    status_id = Column(Integer, ForeignKey(Status.id), nullable=False)
    balance = Column(BigInteger, nullable=False)
    password_hash = Column(String(60), nullable=False)
    failed_password_attempts = Column(SmallInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("account_key"),
        UniqueConstraint("client_id"),
    )

    client = relationship("Client", foreign_keys=[client_id], back_populates="account", lazy="selectin")
    status = relationship("Status", foreign_keys=[status_id], lazy="selectin")
