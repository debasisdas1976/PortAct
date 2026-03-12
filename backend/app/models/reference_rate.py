from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class ReferenceRate(Base):
    """
    Stores current snapshot rates for bank FDs and government savings schemes.
    One row per (category, name) — always reflects the latest known rate.

    category : 'bank_fd' | 'govt_scheme'
    name     : short key, e.g. 'sbi', 'hdfc', 'ppf', 'epf'
    rate     : interest rate in % p.a.
    sub_info : context string — tenure label for bank FDs (e.g. "Best rate p.a."),
               quarter label for govt schemes (e.g. "Jan–Mar 2026")

    Seeded by Alembic migration.
    Refreshed by the monthly (bank FD) and quarterly (govt schemes) scheduler jobs.
    """
    __tablename__ = "reference_rates"

    id         = Column(Integer, primary_key=True, index=True)
    category   = Column(String(30),  nullable=False, index=True)
    name       = Column(String(50),  nullable=False)
    rate       = Column(Float,       nullable=False)
    sub_info   = Column(String(100), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    from sqlalchemy import UniqueConstraint
    __table_args__ = (
        UniqueConstraint('category', 'name', name='uq_reference_rates_category_name'),
    )
