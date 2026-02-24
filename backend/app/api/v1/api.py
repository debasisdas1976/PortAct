from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth, users, assets, transactions, statements, alerts, dashboard, prices,
    bank_accounts, demat_accounts, crypto_accounts, crypto_exchanges, banks, brokers, expense_categories, expenses, bank_statements, ppf, pf, mutual_fund_holdings, ssy, nps,
    gratuity, insurance, fixed_deposit, recurring_deposit, portfolio_admin, settings, real_estate, portfolios, asset_types, institutions,
    system
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
api_router.include_router(crypto_exchanges.router, prefix="/crypto-exchanges", tags=["Crypto Exchanges"])
api_router.include_router(banks.router, prefix="/banks", tags=["Banks"])
api_router.include_router(brokers.router, prefix="/brokers", tags=["Brokers"])
api_router.include_router(expense_categories.router, prefix="/expense-categories", tags=["Expense Categories"])
api_router.include_router(expenses.router, prefix="/expenses", tags=["Expenses"])
api_router.include_router(bank_statements.router, prefix="/bank-statements", tags=["Bank Statements"])
api_router.include_router(ppf.router, prefix="/ppf", tags=["PPF"])
api_router.include_router(pf.router, prefix="/pf", tags=["PF/EPF"])
api_router.include_router(mutual_fund_holdings.router, prefix="/mutual-fund-holdings", tags=["Mutual Fund Holdings"])
api_router.include_router(ssy.router, prefix="/ssy", tags=["SSY"])
api_router.include_router(nps.router, prefix="/nps", tags=["NPS"])
api_router.include_router(gratuity.router, prefix="/gratuity", tags=["Gratuity"])
api_router.include_router(insurance.router, prefix="/insurance", tags=["Insurance"])
api_router.include_router(fixed_deposit.router, prefix="/fixed-deposits", tags=["Fixed Deposits"])
api_router.include_router(recurring_deposit.router, prefix="/recurring-deposits", tags=["Recurring Deposits"])
api_router.include_router(portfolio_admin.router, prefix="/portfolio", tags=["Portfolio Admin"])
api_router.include_router(settings.router, prefix="/settings", tags=["Application Settings"])
api_router.include_router(real_estate.router, prefix="/real-estates", tags=["Real Estate"])
api_router.include_router(portfolios.router, prefix="/portfolios", tags=["Portfolios"])
api_router.include_router(asset_types.router, prefix="/asset-types", tags=["Asset Types"])
api_router.include_router(institutions.router, prefix="/institutions", tags=["Institutions"])
api_router.include_router(system.router, prefix="/system", tags=["System"])

# Made with Bob
