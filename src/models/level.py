from sqlalchemy import BigInteger, Column, DateTime, Integer, SmallInteger, String, UniqueConstraint, func
from models.base import Base


class Level(Base):
    __tablename__ = "level"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)
    description = Column(String(255), nullable=False)
    daily_outflow_limit = Column(BigInteger, nullable=True)
    income_multiple = Column(SmallInteger, nullable=False)
    income_alerts_per_month = Column(SmallInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("enumerator"),)

    SILVER = "silver"
    GOLD = "gold"
