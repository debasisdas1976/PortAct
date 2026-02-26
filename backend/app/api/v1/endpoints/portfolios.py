from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.asset import Asset
from app.models.bank_account import BankAccount
from app.models.demat_account import DematAccount
from app.models.crypto_account import CryptoAccount
from app.models.expense import Expense
from app.schemas.portfolio import (
    Portfolio as PortfolioSchema,
    PortfolioCreate,
    PortfolioUpdate,
    PortfolioWithSummary,
)

router = APIRouter()


@router.get("/", response_model=List[PortfolioWithSummary])
async def get_portfolios(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get all portfolios for the current user, with summary stats."""
    portfolios = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.is_active == True,
    ).order_by(Portfolio.is_default.desc(), Portfolio.name).all()

    result = []
    for p in portfolios:
        assets = db.query(Asset).filter(
            Asset.portfolio_id == p.id,
            Asset.is_active == True,
        ).all()
        result.append(PortfolioWithSummary(
            id=p.id,
            user_id=p.user_id,
            name=p.name,
            description=p.description,
            is_default=p.is_default,
            is_active=p.is_active,
            created_at=p.created_at,
            updated_at=p.updated_at,
            asset_count=len(assets),
            total_invested=sum(a.total_invested or 0 for a in assets),
            total_current_value=sum(a.current_value or 0 for a in assets),
        ))
    return result


@router.get("/{portfolio_id}", response_model=PortfolioSchema)
async def get_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a specific portfolio by ID."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == current_user.id,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


@router.post("/", response_model=PortfolioSchema, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    data: PortfolioCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a new portfolio."""
    existing = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.name == data.name,
        Portfolio.is_active == True,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="A portfolio with this name already exists")

    portfolio = Portfolio(user_id=current_user.id, **data.model_dump())
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.put("/{portfolio_id}", response_model=PortfolioSchema)
async def update_portfolio(
    portfolio_id: int,
    data: PortfolioUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a portfolio. Cannot deactivate the default portfolio."""
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == current_user.id,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    if portfolio.is_default and data.is_active is False:
        raise HTTPException(status_code=400, detail="Cannot deactivate the default portfolio")

    # Check name uniqueness if name is being changed
    update_data = data.model_dump(exclude_unset=True)
    if 'name' in update_data and update_data['name'] != portfolio.name:
        existing = db.query(Portfolio).filter(
            Portfolio.user_id == current_user.id,
            Portfolio.name == update_data['name'],
            Portfolio.is_active == True,
            Portfolio.id != portfolio_id,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="A portfolio with this name already exists")

    for field, value in update_data.items():
        setattr(portfolio, field, value)
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.delete("/{portfolio_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete a portfolio. Assets are moved to the default portfolio.
    Cannot delete the default portfolio.
    """
    portfolio = db.query(Portfolio).filter(
        Portfolio.id == portfolio_id,
        Portfolio.user_id == current_user.id,
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    if portfolio.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete the default portfolio")

    # Move all portfolio-scoped entities to the default portfolio
    default = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.is_default == True,
    ).first()
    for model in (Asset, BankAccount, DematAccount, CryptoAccount, Expense):
        db.query(model).filter(
            model.portfolio_id == portfolio_id
        ).update({model.portfolio_id: default.id}, synchronize_session=False)

    db.delete(portfolio)
    db.commit()
    return None

# Made with Bob
