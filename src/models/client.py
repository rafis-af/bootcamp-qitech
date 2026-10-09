from sqlalchemy import BigInteger, CHAR, Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Level, Status


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True)
    client_key = Column(CHAR(36), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    document_number = Column(CHAR(14), nullable=False)
    birthdate = Column(Date, nullable=False)
    monthly_income = Column(BigInteger, nullable=False)
    status_id = Column(Integer, ForeignKey(Status.id), nullable=False)
    level_id = Column(Integer, ForeignKey(Level.id), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("client_key"),
        UniqueConstraint("document_number"),
        UniqueConstraint("email"),
    )

    status = relationship("Status", foreign_keys=[status_id], lazy="selectin")
    level = relationship("Level", foreign_keys=[level_id], lazy="selectin")

    account = relationship("Account", back_populates="client", uselist=False)
