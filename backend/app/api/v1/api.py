from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, users, assets, transactions, statements, alerts, dashboard, prices,
    bank_accounts, demat_accounts, crypto_accounts, expense_categories, expenses, bank_statements, ppf, pf, mutual_fund_holdings
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(assets.router, prefix="/assets", tags=["Assets"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
api_router.include_router(statements.router, prefix="/statements", tags=["Statements"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(prices.router, prefix="/prices", tags=["Prices"])
api_router.include_router(bank_accounts.router, prefix="/bank-accounts", tags=["Bank Accounts"])
api_router.include_router(demat_accounts.router, prefix="/demat-accounts", tags=["Demat Accounts"])
api_router.include_router(crypto_accounts.router, prefix="/crypto-accounts", tags=["Crypto Accounts"])
api_router.include_router(expense_categories.router, prefix="/expense-categories", tags=["Expense Categories"])
api_router.include_router(expenses.router, prefix="/expenses", tags=["Expenses"])
api_router.include_router(bank_statements.router, prefix="/bank-statements", tags=["Bank Statements"])
api_router.include_router(ppf.router, prefix="/ppf", tags=["PPF"])
api_router.include_router(pf.router, prefix="/pf", tags=["PF/EPF"])
api_router.include_router(mutual_fund_holdings.router, prefix="/mutual-fund-holdings", tags=["Mutual Fund Holdings"])

# Made with Bob
