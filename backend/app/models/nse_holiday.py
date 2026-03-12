from sqlalchemy import Column, Integer, String, Date, Index
from app.core.database import Base


class NseHoliday(Base):
    """NSE trading holidays — populated once per year by the scheduler."""
    __tablename__ = "nse_holidays"

    id   = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    year = Column(Integer, nullable=False)

    __table_args__ = (
        Index("ix_nse_holidays_year", "year"),
    )
