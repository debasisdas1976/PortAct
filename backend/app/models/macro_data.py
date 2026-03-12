from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.core.database import Base


class MacroDataPoint(Base):
    """
    Stores macro-economic time-series data points.

    series  : identifier for the data set ('us_cpi', 'us_unemployment',
                                            'india_cpi', 'rbi_repo_rate')
    period  : calendar period in YYYY-MM format (e.g. '2025-01')
    label   : display label shown on charts    (e.g. "Jan'25")
    value   : the numeric value (YoY % for CPI/inflation, rate % for others)

    Historical data is seeded by the Alembic migration.
    New entries are written by the daily macro refresh scheduler job.
    """
    __tablename__ = "macro_data_points"

    id         = Column(Integer, primary_key=True, index=True)
    series     = Column(String(50), nullable=False, index=True)
    period     = Column(String(10), nullable=False)   # 'YYYY-MM'
    label      = Column(String(20), nullable=False)   # "Jan'25"
    value      = Column(Float,      nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('series', 'period', name='uq_macro_series_period'),
    )
