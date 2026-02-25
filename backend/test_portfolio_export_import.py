#!/usr/bin/env python3
"""
End-to-end test for Portfolio Export / Import (backup & restore).

What this script does
─────────────────────
1. Registers two fresh test users  (source_user, target_user)
2. Populates source_user with representative data for EVERY entity type:
   bank accounts, demat accounts, crypto accounts, assets (multiple types),
   expense categories, expenses, transactions, alerts, portfolio snapshots
   with asset snapshots.
3. Exports source_user's portfolio via GET /portfolio/export.
4. Restores the exported JSON into target_user via POST /portfolio/restore.
5. Exports target_user's portfolio and compares the two payloads field-by-field.
6. Runs the restore a second time to verify idempotency (all records skipped).
7. Cleans up both test users from the database.

Run
───
    cd backend
    python test_portfolio_export_import.py

Requirements
────────────
- The backend server must be running at http://localhost:8000
- A valid DATABASE_URL must be set in .env (used only for cleanup)
"""
from __future__ import annotations

import json
import sys
import os
import uuid
import traceback
from datetime import datetime, timedelta, date
from typing import Any, Dict, Optional

import requests

# ── Configuration ──────────────────────────────────────────────────────────
BASE_URL = os.environ.get("TEST_API_URL", "http://localhost:8000/api/v1")
UNIQUE = uuid.uuid4().hex[:8]
SOURCE_USER = {"email": f"test_src_{UNIQUE}@test.com", "username": f"test_src_{UNIQUE}", "password": "TestPass123!", "full_name": "Test Source User"}
TARGET_USER = {"email": f"test_tgt_{UNIQUE}@test.com", "username": f"test_tgt_{UNIQUE}", "password": "TestPass123!", "full_name": "Test Target User"}

# Counters
passed = 0
failed = 0
errors: list[str] = []


def ok(label: str):
    global passed
    passed += 1
    print(f"  ✓ {label}")


def fail(label: str, detail: str = ""):
    global failed
    failed += 1
    msg = f"  ✗ {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    errors.append(msg)


# ── HTTP helpers ───────────────────────────────────────────────────────────
class APIClient:
    def __init__(self):
        self.token: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def register(self, user: dict) -> dict:
        r = requests.post(f"{BASE_URL}/auth/register", json=user, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def login(self, username: str, password: str) -> str:
        r = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        self.token = r.json()["access_token"]
        return self.token

    def get(self, path: str, **kwargs) -> requests.Response:
        return requests.get(f"{BASE_URL}{path}", headers=self._headers(), **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return requests.post(f"{BASE_URL}{path}", headers=self._headers(), **kwargs)

    def post_json(self, path: str, data: dict) -> requests.Response:
        return requests.post(f"{BASE_URL}{path}", json=data, headers=self._headers())

    def put_json(self, path: str, data: dict) -> requests.Response:
        return requests.put(f"{BASE_URL}{path}", json=data, headers=self._headers())

    def delete(self, path: str) -> requests.Response:
        return requests.delete(f"{BASE_URL}{path}", headers=self._headers())


# ── Seed data creation ────────────────────────────────────────────────────
def seed_data(api: APIClient) -> Dict[str, Any]:
    """Create representative records for every entity type. Returns created IDs."""
    ids: Dict[str, Any] = {}

    # 1. Bank accounts
    ba1 = api.post_json("/bank-accounts", {
        "bank_name": "hdfc_bank",
        "account_type": "savings",
        "account_number": f"HDFC{UNIQUE}001",
        "account_holder_name": "Test Source User",
        "ifsc_code": "HDFC0001234",
        "branch_name": "Test Branch",
        "current_balance": 150000.50,
        "available_balance": 145000.00,
        "credit_limit": 0,
        "is_active": True,
        "is_primary": True,
        "nickname": "My Savings",
        "notes": "Primary savings account",
    })
    ba1.raise_for_status()
    ids["ba1"] = ba1.json()["id"]

    ba2 = api.post_json("/bank-accounts", {
        "bank_name": "icici_bank",
        "account_type": "credit_card",
        "account_number": f"ICICI{UNIQUE}002",
        "account_holder_name": "Test Source User",
        "ifsc_code": "ICIC0001234",
        "branch_name": "CC Branch",
        "current_balance": -25000.00,
        "available_balance": 75000.00,
        "credit_limit": 100000.00,
        "is_active": True,
        "is_primary": False,
        "nickname": "My CC",
        "notes": "Credit card notes",
    })
    ba2.raise_for_status()
    ids["ba2"] = ba2.json()["id"]

    # 2. Demat accounts
    da1 = api.post_json("/demat-accounts", {
        "broker_name": "zerodha",
        "account_id": f"ZRD{UNIQUE}",
        "account_holder_name": "Test Source User",
        "demat_account_number": f"1201{UNIQUE}",
        "cash_balance": 50000.00,
        "currency": "INR",
        "is_active": True,
        "is_primary": True,
        "nickname": "Zerodha Main",
        "notes": "Main trading account",
    })
    da1.raise_for_status()
    ids["da1"] = da1.json()["id"]

    da2 = api.post_json("/demat-accounts", {
        "broker_name": "vested",
        "account_id": f"VST{UNIQUE}",
        "account_holder_name": "Test Source User",
        "demat_account_number": f"VST{UNIQUE}",
        "cash_balance": 0,
        "cash_balance_usd": 1250.50,
        "currency": "USD",
        "is_active": True,
        "is_primary": False,
        "nickname": "US Stocks",
        "notes": "US market account",
    })
    da2.raise_for_status()
    ids["da2"] = da2.json()["id"]

    # 3. Crypto accounts
    ca1 = api.post_json("/crypto-accounts", {
        "exchange_name": "binance",
        "account_id": f"BIN{UNIQUE}",
        "account_holder_name": "Test Source User",
        "wallet_address": f"0xDEADBEEF{UNIQUE}",
        "cash_balance_usd": 500.00,
        "total_value_usd": 12500.00,
        "is_active": True,
        "is_primary": True,
        "nickname": "Binance Main",
        "notes": "Main crypto exchange",
    })
    ca1.raise_for_status()
    ids["ca1"] = ca1.json()["id"]

    # 4. Assets — multiple types
    # Stock
    a_stock = api.post_json("/assets", {
        "asset_type": "stock",
        "name": f"Reliance Industries {UNIQUE}",
        "symbol": "RELIANCE",
        "api_symbol": "RELIANCE.NS",
        "isin": "INE002A01018",
        "quantity": 10,
        "purchase_price": 2500.00,
        "current_price": 2750.00,
        "total_invested": 25000.00,
        "details": {"sector": "Energy", "market_cap": "large"},
        "notes": "Blue chip stock",
        "purchase_date": "2024-03-15T00:00:00",
        "account_id": f"ZRD{UNIQUE}",
        "broker_name": "zerodha",
        "account_holder_name": "Test Source User",
    })
    a_stock.raise_for_status()
    ids["a_stock"] = a_stock.json()["id"]

    # US Stock
    a_us = api.post_json("/assets", {
        "asset_type": "us_stock",
        "name": f"Apple Inc {UNIQUE}",
        "symbol": "AAPL",
        "api_symbol": "AAPL",
        "isin": "US0378331005",
        "quantity": 5,
        "purchase_price": 180.00,
        "current_price": 195.00,
        "total_invested": 900.00,
        "details": {"currency": "USD"},
        "notes": "US tech stock",
        "purchase_date": "2024-06-01T00:00:00",
        "account_id": f"VST{UNIQUE}",
        "broker_name": "vested",
        "account_holder_name": "Test Source User",
    })
    a_us.raise_for_status()
    ids["a_us"] = a_us.json()["id"]

    # Equity Mutual Fund
    a_mf = api.post_json("/assets", {
        "asset_type": "equity_mutual_fund",
        "name": f"Axis Bluechip Fund {UNIQUE}",
        "symbol": "AXISBLU",
        "api_symbol": "120503",
        "isin": "INF846K01EW2",
        "quantity": 150.5,
        "purchase_price": 42.50,
        "current_price": 48.00,
        "total_invested": 6396.25,
        "details": {"fund_house": "Axis AMC", "category": "Large Cap"},
        "notes": "SIP fund",
        "purchase_date": "2023-01-01T00:00:00",
    })
    a_mf.raise_for_status()
    ids["a_mf"] = a_mf.json()["id"]

    # Crypto
    a_crypto = api.post_json("/assets", {
        "asset_type": "crypto",
        "name": f"Bitcoin {UNIQUE}",
        "symbol": "BTC",
        "api_symbol": "bitcoin",
        "quantity": 0.05,
        "purchase_price": 45000.00,
        "current_price": 62000.00,
        "total_invested": 2250.00,
        "details": {"network": "Bitcoin"},
        "notes": "HODLing",
        "purchase_date": "2024-01-15T00:00:00",
        "account_id": f"BIN{UNIQUE}",
        "broker_name": "binance",
    })
    a_crypto.raise_for_status()
    ids["a_crypto"] = a_crypto.json()["id"]

    # PPF
    a_ppf = api.post_json("/assets", {
        "asset_type": "ppf",
        "name": f"PPF Account {UNIQUE}",
        "symbol": "PPF",
        "quantity": 1,
        "purchase_price": 500000,
        "current_price": 500000,
        "total_invested": 500000,
        "details": {"maturity_date": "2035-04-01", "interest_rate": 7.1},
        "notes": "15 year PPF",
        "purchase_date": "2020-04-01T00:00:00",
    })
    a_ppf.raise_for_status()
    ids["a_ppf"] = a_ppf.json()["id"]

    # Fixed Deposit
    a_fd = api.post_json("/assets", {
        "asset_type": "fixed_deposit",
        "name": f"HDFC FD {UNIQUE}",
        "symbol": "FD-HDFC",
        "quantity": 1,
        "purchase_price": 200000,
        "current_price": 200000,
        "total_invested": 200000,
        "details": {"interest_rate": 7.25, "maturity_date": "2026-03-15", "tenure_months": 24},
        "notes": "2 year FD",
        "purchase_date": "2024-03-15T00:00:00",
    })
    a_fd.raise_for_status()
    ids["a_fd"] = a_fd.json()["id"]

    # Insurance
    a_ins = api.post_json("/assets", {
        "asset_type": "insurance_policy",
        "name": f"LIC Policy {UNIQUE}",
        "symbol": "LIC-001",
        "quantity": 1,
        "purchase_price": 100000,
        "current_price": 120000,
        "total_invested": 100000,
        "details": {"policy_number": "LIC123456", "premium": 10000, "sum_assured": 500000},
        "notes": "Endowment policy",
        "purchase_date": "2019-01-01T00:00:00",
    })
    a_ins.raise_for_status()
    ids["a_ins"] = a_ins.json()["id"]

    # NPS
    a_nps = api.post_json("/assets", {
        "asset_type": "nps",
        "name": f"NPS Tier 1 {UNIQUE}",
        "symbol": "NPS-T1",
        "quantity": 1,
        "purchase_price": 300000,
        "current_price": 350000,
        "total_invested": 300000,
        "details": {"pran_number": "NPS12345678", "fund_manager": "SBI Pension"},
        "notes": "Retirement fund",
        "purchase_date": "2021-04-01T00:00:00",
    })
    a_nps.raise_for_status()
    ids["a_nps"] = a_nps.json()["id"]

    # ESOP
    a_esop = api.post_json("/assets", {
        "asset_type": "esop",
        "name": f"Startup ESOPs {UNIQUE}",
        "symbol": "ESOP-001",
        "quantity": 5000,
        "purchase_price": 10.00,
        "current_price": 45.00,
        "total_invested": 50000.00,
        "details": {"grant_date": "2022-01-15", "vesting_schedule": "4 years", "cliff_months": 12, "strike_price": 10.00},
        "notes": "Employee stock options",
        "purchase_date": "2022-01-15T00:00:00",
    })
    a_esop.raise_for_status()
    ids["a_esop"] = a_esop.json()["id"]

    # RSU
    a_rsu = api.post_json("/assets", {
        "asset_type": "rsu",
        "name": f"Company RSUs {UNIQUE}",
        "symbol": "RSU-001",
        "quantity": 200,
        "purchase_price": 0,
        "current_price": 150.00,
        "total_invested": 0,
        "details": {"grant_date": "2023-06-01", "vesting_schedule": "4 years", "shares_vested": 50},
        "notes": "Restricted stock units",
        "purchase_date": "2023-06-01T00:00:00",
    })
    a_rsu.raise_for_status()
    ids["a_rsu"] = a_rsu.json()["id"]

    # Hybrid Mutual Fund
    a_hybrid_mf = api.post_json("/assets", {
        "asset_type": "hybrid_mutual_fund",
        "name": f"ICICI Balanced Advantage {UNIQUE}",
        "symbol": "ICICIBAF",
        "api_symbol": "120587",
        "isin": "INF109K01BD8",
        "quantity": 500,
        "purchase_price": 35.00,
        "current_price": 42.50,
        "total_invested": 17500.00,
        "details": {"fund_house": "ICICI Prudential", "category": "Balanced Advantage"},
        "notes": "Hybrid balanced fund",
        "purchase_date": "2023-06-01T00:00:00",
    })
    a_hybrid_mf.raise_for_status()
    ids["a_hybrid_mf"] = a_hybrid_mf.json()["id"]

    # Debt Mutual Fund
    a_debt_mf = api.post_json("/assets", {
        "asset_type": "debt_mutual_fund",
        "name": f"HDFC Short Term Debt {UNIQUE}",
        "symbol": "HDFCSTD",
        "api_symbol": "119065",
        "isin": "INF179K01BY2",
        "quantity": 1000,
        "purchase_price": 25.00,
        "current_price": 27.50,
        "total_invested": 25000.00,
        "details": {"fund_house": "HDFC AMC", "category": "Short Duration"},
        "notes": "Debt fund for stability",
        "purchase_date": "2024-01-01T00:00:00",
    })
    a_debt_mf.raise_for_status()
    ids["a_debt_mf"] = a_debt_mf.json()["id"]

    # Sovereign Gold Bond
    a_sgb = api.post_json("/assets", {
        "asset_type": "sovereign_gold_bond",
        "name": f"SGB 2024-25 Series I {UNIQUE}",
        "symbol": "SGB2024",
        "quantity": 5,
        "purchase_price": 6263.00,
        "current_price": 7100.00,
        "total_invested": 31315.00,
        "details": {"series": "2024-25 Series I", "maturity_date": "2032-03-15", "interest_rate": 2.5},
        "notes": "Gold bond investment",
        "purchase_date": "2024-03-01T00:00:00",
    })
    a_sgb.raise_for_status()
    ids["a_sgb"] = a_sgb.json()["id"]

    # Corporate Bond
    a_corp_bond = api.post_json("/assets", {
        "asset_type": "corporate_bond",
        "name": f"HDFC Corp Bond {UNIQUE}",
        "symbol": "HDFCBOND",
        "quantity": 10,
        "purchase_price": 1000.00,
        "current_price": 1050.00,
        "total_invested": 10000.00,
        "details": {"coupon_rate": 8.5, "maturity_date": "2027-06-15", "credit_rating": "AAA"},
        "notes": "Corporate bond",
        "purchase_date": "2024-06-15T00:00:00",
    })
    a_corp_bond.raise_for_status()
    ids["a_corp_bond"] = a_corp_bond.json()["id"]

    # 5. Transactions
    txns = [
        {"asset_id": ids["a_stock"], "transaction_type": "buy", "transaction_date": "2024-03-15T10:30:00",
         "quantity": 5, "price_per_unit": 2500, "total_amount": 12500, "fees": 50, "taxes": 25,
         "description": "First buy", "reference_number": f"TXN{UNIQUE}001", "notes": "Initial purchase"},
        {"asset_id": ids["a_stock"], "transaction_type": "buy", "transaction_date": "2024-06-15T10:30:00",
         "quantity": 5, "price_per_unit": 2500, "total_amount": 12500, "fees": 50, "taxes": 25,
         "description": "Second buy", "reference_number": f"TXN{UNIQUE}002", "notes": "Averaging"},
        {"asset_id": ids["a_stock"], "transaction_type": "dividend", "transaction_date": "2024-09-01T00:00:00",
         "quantity": 0, "price_per_unit": 0, "total_amount": 100, "fees": 0, "taxes": 10,
         "description": "Dividend Q2", "reference_number": f"TXN{UNIQUE}003", "notes": "Quarterly dividend"},
        {"asset_id": ids["a_mf"], "transaction_type": "buy", "transaction_date": "2023-01-05T00:00:00",
         "quantity": 150.5, "price_per_unit": 42.50, "total_amount": 6396.25, "fees": 0, "taxes": 0,
         "description": "SIP purchase", "reference_number": f"TXN{UNIQUE}004"},
        {"asset_id": ids["a_crypto"], "transaction_type": "buy", "transaction_date": "2024-01-15T14:00:00",
         "quantity": 0.05, "price_per_unit": 45000, "total_amount": 2250, "fees": 5, "taxes": 0,
         "description": "BTC purchase", "reference_number": f"TXN{UNIQUE}005"},
    ]
    for t in txns:
        r = api.post_json("/transactions", t)
        r.raise_for_status()

    # 6. Expense categories
    cat1 = api.post_json("/expense-categories", {
        "name": f"Groceries {UNIQUE}",
        "description": "Food and grocery shopping",
        "icon": "cart",
        "color": "#4CAF50",
        "is_income": False,
        "is_active": True,
        "keywords": "grocery,food,supermarket",
    })
    cat1.raise_for_status()
    ids["cat1"] = cat1.json()["id"]

    cat2 = api.post_json("/expense-categories", {
        "name": f"Salary {UNIQUE}",
        "description": "Monthly salary",
        "icon": "money",
        "color": "#2196F3",
        "is_income": True,
        "is_active": True,
        "keywords": "salary,income,pay",
    })
    cat2.raise_for_status()
    ids["cat2"] = cat2.json()["id"]

    # Sub-category
    cat3 = api.post_json("/expense-categories", {
        "name": f"Vegetables {UNIQUE}",
        "description": "Vegetable shopping",
        "icon": "leaf",
        "color": "#66BB6A",
        "parent_id": ids["cat1"],
        "is_income": False,
        "is_active": True,
        "keywords": "vegetable,sabzi",
    })
    cat3.raise_for_status()
    ids["cat3"] = cat3.json()["id"]

    # 7. Expenses
    expenses = [
        {
            "bank_account_id": ids["ba1"],
            "category_id": ids["cat1"],
            "transaction_date": "2024-12-01T10:30:00",
            "transaction_type": "debit",
            "amount": 2500.00,
            "balance_after": 147500.50,
            "description": "BigBasket order",
            "merchant_name": "BigBasket",
            "reference_number": f"EXP{UNIQUE}001",
            "payment_method": "upi",
            "is_recurring": True,
            "is_split": False,
            "location": "Mumbai",
            "notes": "Weekly groceries",
            "tags": "food,weekly",
        },
        {
            "bank_account_id": ids["ba1"],
            "category_id": ids["cat2"],
            "transaction_date": "2024-12-01T00:00:00",
            "transaction_type": "credit",
            "amount": 100000.00,
            "balance_after": 247500.50,
            "description": "Salary December",
            "merchant_name": "Employer Corp",
            "reference_number": f"EXP{UNIQUE}002",
            "payment_method": "net_banking",
            "is_recurring": True,
            "is_split": False,
            "location": "",
            "notes": "Monthly salary",
            "tags": "salary,income",
        },
        {
            "bank_account_id": ids["ba2"],
            "category_id": ids["cat3"],
            "transaction_date": "2024-12-05T18:00:00",
            "transaction_type": "debit",
            "amount": 450.00,
            "balance_after": -25450.00,
            "description": "Vegetable market",
            "merchant_name": "Local Market",
            "reference_number": f"EXP{UNIQUE}003",
            "payment_method": "credit_card",
            "is_recurring": False,
            "is_split": True,
            "location": "Andheri, Mumbai",
            "notes": "Split with roommate",
            "tags": "food,vegetables,split",
        },
    ]
    for exp in expenses:
        r = api.post_json("/expenses", exp)
        r.raise_for_status()

    # 8. Alerts — created directly via DB since there may not be a create endpoint
    # We'll inject them via the database for completeness
    _seed_alerts_and_snapshots_via_db(ids)

    return ids


def _seed_alerts_and_snapshots_via_db(ids: Dict[str, Any]):
    """Seed alerts, portfolio snapshots, and mutual fund holdings directly via DB.
    These don't have public create endpoints, so we insert directly."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.models.alert import Alert
    from app.models.portfolio_snapshot import PortfolioSnapshot, AssetSnapshot
    from app.models.mutual_fund_holding import MutualFundHolding

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Find our source user
        from app.models.user import User
        user = db.query(User).filter(User.username == SOURCE_USER["username"]).first()
        if not user:
            print("  ⚠ Could not find source user for alert/snapshot seeding")
            return

        uid = user.id

        # Create alerts
        alerts_data = [
            {
                "user_id": uid,
                "asset_id": ids["a_stock"],
                "alert_type": "price_change",
                "severity": "warning",
                "title": "Reliance price dropped 5%",
                "message": "Reliance Industries fell 5% today due to quarterly results.",
                "suggested_action": "Consider buying the dip if fundamentals are strong.",
                "action_url": "/assets",
                "is_read": False,
                "is_dismissed": False,
                "is_actionable": True,
            },
            {
                "user_id": uid,
                "asset_id": ids["a_fd"],
                "alert_type": "maturity_reminder",
                "severity": "info",
                "title": "FD maturing in 30 days",
                "message": "Your HDFC FD is maturing on 2026-03-15. Plan reinvestment.",
                "suggested_action": "Renew FD or redirect to another investment.",
                "is_read": True,
                "is_dismissed": False,
                "is_actionable": True,
            },
            {
                "user_id": uid,
                "asset_id": None,
                "alert_type": "market_volatility",
                "severity": "critical",
                "title": "Market volatility alert",
                "message": "Nifty 50 index has shown high volatility. VIX above 20.",
                "suggested_action": "Review portfolio exposure and hedging.",
                "is_read": False,
                "is_dismissed": True,
                "is_actionable": False,
            },
        ]
        for ad in alerts_data:
            db.add(Alert(**ad))
        db.flush()

        # Create mutual fund holdings for the equity MF asset
        mf_holdings_data = [
            {
                "asset_id": ids["a_mf"],
                "user_id": uid,
                "stock_name": "Reliance Industries",
                "stock_symbol": "RELIANCE",
                "isin": "INE002A01018",
                "holding_percentage": 8.5,
                "holding_value": 543.68,
                "quantity_held": 0.2,
                "sector": "Energy",
                "industry": "Oil & Gas",
                "market_cap": "Large",
                "stock_current_price": 2750.00,
                "data_source": "mfapi",
            },
            {
                "asset_id": ids["a_mf"],
                "user_id": uid,
                "stock_name": "HDFC Bank",
                "stock_symbol": "HDFCBANK",
                "isin": "INE040A01034",
                "holding_percentage": 7.2,
                "holding_value": 460.53,
                "quantity_held": 0.28,
                "sector": "Financial Services",
                "industry": "Banking",
                "market_cap": "Large",
                "stock_current_price": 1650.00,
                "data_source": "mfapi",
            },
            {
                "asset_id": ids["a_mf"],
                "user_id": uid,
                "stock_name": "Infosys",
                "stock_symbol": "INFY",
                "isin": "INE009A01021",
                "holding_percentage": 6.1,
                "holding_value": 390.17,
                "quantity_held": 0.22,
                "sector": "IT",
                "industry": "IT Services",
                "market_cap": "Large",
                "stock_current_price": 1780.00,
                "data_source": "mfapi",
            },
        ]
        for mfh in mf_holdings_data:
            db.add(MutualFundHolding(**mfh))
        db.flush()

        # Create portfolio snapshots with asset snapshots
        today = date.today()
        for days_ago in [7, 3, 1]:
            snap_date = today - timedelta(days=days_ago)
            ps = PortfolioSnapshot(
                user_id=uid,
                snapshot_date=snap_date,
                total_invested=1034546.25 + days_ago * 100,
                total_current_value=1117750.00 + days_ago * 200,
                total_profit_loss=83203.75 + days_ago * 100,
                total_profit_loss_percentage=8.04 + days_ago * 0.1,
                total_assets_count=8,
            )
            db.add(ps)
            db.flush()

            # Asset snapshots for each portfolio snapshot
            asset_snap_data = [
                {"asset_type": "stock", "asset_name": f"Reliance Industries {UNIQUE}",
                 "asset_symbol": "RELIANCE", "quantity": 10, "purchase_price": 2500,
                 "current_price": 2750 + days_ago * 10, "total_invested": 25000,
                 "current_value": 27500 + days_ago * 100},
                {"asset_type": "equity_mutual_fund", "asset_name": f"Axis Bluechip Fund {UNIQUE}",
                 "asset_symbol": "AXISBLU", "quantity": 150.5, "purchase_price": 42.50,
                 "current_price": 48.00 + days_ago * 0.5, "total_invested": 6396.25,
                 "current_value": 7224.00 + days_ago * 75},
                {"asset_type": "crypto", "asset_name": f"Bitcoin {UNIQUE}",
                 "asset_symbol": "BTC", "quantity": 0.05, "purchase_price": 45000,
                 "current_price": 62000 + days_ago * 500, "total_invested": 2250,
                 "current_value": 3100 + days_ago * 25},
            ]
            for asd in asset_snap_data:
                asd["profit_loss"] = asd["current_value"] - asd["total_invested"]
                asd["profit_loss_percentage"] = (
                    (asd["profit_loss"] / asd["total_invested"] * 100) if asd["total_invested"] else 0
                )
                a_snap = AssetSnapshot(
                    portfolio_snapshot_id=ps.id,
                    snapshot_date=snap_date,
                    **asd,
                )
                db.add(a_snap)

        db.commit()
        print("  ✓ Seeded alerts, mutual fund holdings, and portfolio snapshots via DB")
    except Exception as e:
        db.rollback()
        print(f"  ⚠ Error seeding alerts/snapshots: {e}")
        traceback.print_exc()
    finally:
        db.close()


# ── Comparison helpers ────────────────────────────────────────────────────
def compare_entity_lists(
    label: str,
    source_list: list,
    target_list: list,
    key_fields: list[str],
    value_fields: list[str],
    skip_fields: set[str] | None = None,
):
    """Compare two lists of dicts by matching on key_fields, then checking value_fields."""
    skip = skip_fields or set()

    if len(source_list) != len(target_list):
        fail(f"{label}: count mismatch", f"source={len(source_list)}, target={len(target_list)}")
        return

    ok(f"{label}: count matches ({len(source_list)})")

    # Build lookup from target
    def make_key(item):
        return tuple(str(item.get(k, "")) for k in key_fields)

    target_by_key = {}
    for item in target_list:
        target_by_key[make_key(item)] = item

    mismatches = 0
    for src_item in source_list:
        key = make_key(src_item)
        tgt_item = target_by_key.get(key)
        if not tgt_item:
            fail(f"{label}: missing record with key {dict(zip(key_fields, key))}")
            mismatches += 1
            continue

        for field in value_fields:
            if field in skip:
                continue
            src_val = src_item.get(field)
            tgt_val = tgt_item.get(field)
            # Normalize None vs missing
            if src_val is None and tgt_val is None:
                continue
            # Numeric tolerance
            if isinstance(src_val, (int, float)) and isinstance(tgt_val, (int, float)):
                if abs(src_val - tgt_val) > 0.01:
                    fail(f"{label}.{field}: value mismatch for key {dict(zip(key_fields, key))}",
                         f"source={src_val}, target={tgt_val}")
                    mismatches += 1
                continue
            if str(src_val) != str(tgt_val):
                fail(f"{label}.{field}: value mismatch for key {dict(zip(key_fields, key))}",
                     f"source={src_val!r}, target={tgt_val!r}")
                mismatches += 1

    if mismatches == 0:
        ok(f"{label}: all field values match")


# ── Cleanup ──────────────────────────────────────────────────────────────
def cleanup_users():
    """Remove test users and all their data from the DB."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.models.user import User

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        for uname in [SOURCE_USER["username"], TARGET_USER["username"]]:
            u = db.query(User).filter(User.username == uname).first()
            if u:
                db.delete(u)
                print(f"  Cleaned up user: {uname}")
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"  ⚠ Cleanup error: {e}")
    finally:
        db.close()


# ── Main test flow ───────────────────────────────────────────────────────
def main():
    global passed, failed

    print("=" * 72)
    print("PORTFOLIO EXPORT / IMPORT — END-TO-END TEST")
    print("=" * 72)
    print(f"API: {BASE_URL}")
    print(f"Unique suffix: {UNIQUE}")
    print()

    src_api = APIClient()
    tgt_api = APIClient()

    try:
        # ── Step 1: Register users ────────────────────────────────────────
        print("STEP 1: Register test users")
        src_api.register(SOURCE_USER)
        ok("Source user registered")
        tgt_api.register(TARGET_USER)
        ok("Target user registered")

        src_api.login(SOURCE_USER["username"], SOURCE_USER["password"])
        ok("Source user logged in")
        tgt_api.login(TARGET_USER["username"], TARGET_USER["password"])
        ok("Target user logged in")
        print()

        # ── Step 2: Seed source user data ─────────────────────────────────
        print("STEP 2: Seed data for source user")
        seed_ids = seed_data(src_api)
        ok(f"Created {len(seed_ids)} entity groups")
        print()

        # ── Step 3: Export source portfolio ───────────────────────────────
        print("STEP 3: Export source user portfolio")
        export_resp = src_api.get("/portfolio/export")
        export_resp.raise_for_status()
        source_payload = export_resp.json()

        if source_payload.get("export_version") == "4.0":
            ok("Export version is 4.0")
        else:
            fail("Export version", f"got {source_payload.get('export_version')}")

        section_checks = [
            ("bank_accounts", 2),
            ("demat_accounts", 2),
            ("crypto_accounts", 1),
            ("assets", 14),
            ("expense_categories", 3),
            ("expenses", 3),
            ("transactions", 5),
            ("mutual_fund_holdings", 3),
            ("alerts", 3),
            ("portfolio_snapshots", 3),
        ]
        for section, expected_count in section_checks:
            actual = len(source_payload.get(section, []))
            if actual == expected_count:
                ok(f"Export contains {actual} {section}")
            else:
                fail(f"Export {section} count", f"expected {expected_count}, got {actual}")

        # Check asset_snapshots nested within portfolio_snapshots
        total_asset_snaps = sum(
            len(ps.get("asset_snapshots", []))
            for ps in source_payload.get("portfolio_snapshots", [])
        )
        if total_asset_snaps == 9:  # 3 snapshots × 3 assets each
            ok(f"Export contains {total_asset_snaps} asset snapshots (nested)")
        else:
            fail("Export asset_snapshots count", f"expected 9, got {total_asset_snaps}")

        # Save export file for inspection
        export_file = f"/tmp/portfolio_test_export_{UNIQUE}.json"
        with open(export_file, "w") as f:
            json.dump(source_payload, f, indent=2)
        ok(f"Export saved to {export_file}")
        print()

        # ── Step 4: Restore into target user ──────────────────────────────
        print("STEP 4: Restore exported data into target user")
        with open(export_file, "rb") as f:
            restore_resp = tgt_api.post(
                "/portfolio/restore",
                files={"file": ("export.json", f, "application/json")},
            )
        restore_resp.raise_for_status()
        restore_data = restore_resp.json()

        if restore_data.get("success"):
            ok("Restore reported success")
        else:
            fail("Restore success flag", str(restore_data))

        stats = restore_data.get("stats", {})
        for entity, expected in [
            ("bank_accounts", 2), ("demat_accounts", 2), ("crypto_accounts", 1),
            ("assets", 14), ("expense_categories", 3), ("expenses", 3),
            ("transactions", 5), ("mutual_fund_holdings", 3),
            ("alerts", 3), ("portfolio_snapshots", 3),
            ("asset_snapshots", 9),
        ]:
            imported = stats.get(entity, {}).get("imported", 0)
            skipped = stats.get(entity, {}).get("skipped", 0)
            if imported == expected and skipped == 0:
                ok(f"Restore {entity}: {imported} imported, {skipped} skipped")
            else:
                fail(f"Restore {entity}", f"imported={imported} (expected {expected}), skipped={skipped}")
        print()

        # ── Step 5: Export target and compare ─────────────────────────────
        print("STEP 5: Export target user and compare")
        target_export = tgt_api.get("/portfolio/export")
        target_export.raise_for_status()
        target_payload = target_export.json()

        # IDs and user_id will differ — we compare by natural keys and values
        id_fields = {"id", "user_id", "statement_id", "demat_account_id",
                     "crypto_account_id", "bank_account_id", "category_id",
                     "asset_id", "portfolio_snapshot_id",
                     "created_at", "updated_at", "last_updated",
                     "exported_at", "exported_by"}

        compare_entity_lists(
            "bank_accounts",
            source_payload["bank_accounts"], target_payload["bank_accounts"],
            key_fields=["bank_name", "account_number"],
            value_fields=["account_type", "account_holder_name", "ifsc_code", "branch_name",
                          "current_balance", "available_balance", "credit_limit",
                          "is_active", "is_primary", "nickname", "notes"],
        )
        compare_entity_lists(
            "demat_accounts",
            source_payload["demat_accounts"], target_payload["demat_accounts"],
            key_fields=["broker_name", "account_id"],
            value_fields=["account_holder_name", "demat_account_number", "cash_balance",
                          "cash_balance_usd", "currency", "is_active", "is_primary", "nickname", "notes"],
        )
        compare_entity_lists(
            "crypto_accounts",
            source_payload["crypto_accounts"], target_payload["crypto_accounts"],
            key_fields=["exchange_name", "account_id"],
            value_fields=["account_holder_name", "wallet_address", "cash_balance_usd",
                          "total_value_usd", "is_active", "is_primary", "nickname", "notes"],
        )
        compare_entity_lists(
            "assets",
            source_payload["assets"], target_payload["assets"],
            key_fields=["asset_type", "name"],
            value_fields=["symbol", "api_symbol", "isin", "quantity", "purchase_price",
                          "current_price", "total_invested", "current_value", "profit_loss",
                          "profit_loss_percentage", "is_active", "notes", "details",
                          "account_id", "broker_name", "account_holder_name"],
        )
        compare_entity_lists(
            "expense_categories",
            source_payload["expense_categories"], target_payload["expense_categories"],
            key_fields=["name"],
            value_fields=["description", "icon", "color", "is_income", "is_active", "keywords"],
        )

        # For expenses, key by description + amount since bank_account_id will differ
        compare_entity_lists(
            "expenses",
            source_payload["expenses"], target_payload["expenses"],
            key_fields=["description", "amount"],
            value_fields=["transaction_type", "balance_after", "merchant_name",
                          "reference_number", "payment_method", "is_categorized",
                          "is_recurring", "is_split", "is_reconciled", "location",
                          "notes", "tags"],
        )

        # For transactions, key by description + total_amount
        compare_entity_lists(
            "transactions",
            source_payload["transactions"], target_payload["transactions"],
            key_fields=["description", "total_amount"],
            value_fields=["transaction_type", "quantity", "price_per_unit",
                          "fees", "taxes", "reference_number", "notes"],
        )

        # Mutual fund holdings, key by stock_name + stock_symbol
        compare_entity_lists(
            "mutual_fund_holdings",
            source_payload["mutual_fund_holdings"], target_payload["mutual_fund_holdings"],
            key_fields=["stock_name", "stock_symbol"],
            value_fields=["isin", "holding_percentage", "holding_value", "quantity_held",
                          "sector", "industry", "market_cap", "stock_current_price",
                          "data_source"],
        )

        compare_entity_lists(
            "alerts",
            source_payload["alerts"], target_payload["alerts"],
            key_fields=["title", "alert_type"],
            value_fields=["severity", "message", "suggested_action",
                          "is_read", "is_dismissed", "is_actionable"],
        )

        # Compare portfolio snapshots by date
        compare_entity_lists(
            "portfolio_snapshots",
            source_payload["portfolio_snapshots"], target_payload["portfolio_snapshots"],
            key_fields=["snapshot_date"],
            value_fields=["total_invested", "total_current_value", "total_profit_loss",
                          "total_profit_loss_percentage", "total_assets_count"],
        )

        # Flatten asset snapshots for comparison
        src_asset_snaps = []
        for ps in source_payload.get("portfolio_snapshots", []):
            for a_snap in ps.get("asset_snapshots", []):
                a_snap["_parent_date"] = ps["snapshot_date"]
                src_asset_snaps.append(a_snap)
        tgt_asset_snaps = []
        for ps in target_payload.get("portfolio_snapshots", []):
            for a_snap in ps.get("asset_snapshots", []):
                a_snap["_parent_date"] = ps["snapshot_date"]
                tgt_asset_snaps.append(a_snap)
        compare_entity_lists(
            "asset_snapshots",
            src_asset_snaps, tgt_asset_snaps,
            key_fields=["_parent_date", "asset_name", "asset_type"],
            value_fields=["asset_symbol", "quantity", "purchase_price", "current_price",
                          "total_invested", "current_value", "profit_loss", "profit_loss_percentage"],
        )
        print()

        # ── Step 6: Idempotency — restore again, all should be skipped ───
        print("STEP 6: Idempotency check — restore again into target user")
        with open(export_file, "rb") as f:
            idem_resp = tgt_api.post(
                "/portfolio/restore",
                files={"file": ("export.json", f, "application/json")},
            )
        idem_resp.raise_for_status()
        idem_data = idem_resp.json()
        idem_stats = idem_data.get("stats", {})

        all_skipped = True
        for entity in ["bank_accounts", "demat_accounts", "crypto_accounts",
                       "assets", "expense_categories", "expenses", "transactions",
                       "mutual_fund_holdings", "alerts", "portfolio_snapshots"]:
            imp = idem_stats.get(entity, {}).get("imported", 0)
            skp = idem_stats.get(entity, {}).get("skipped", 0)
            if imp > 0:
                fail(f"Idempotency {entity}", f"{imp} records imported on second restore (expected 0)")
                all_skipped = False
            else:
                ok(f"Idempotency {entity}: 0 imported, {skp} skipped")
        if all_skipped:
            ok("Idempotency check passed — no duplicates created")
        print()

    except requests.HTTPError as e:
        fail("HTTP error", f"{e.response.status_code}: {e.response.text[:300]}")
        traceback.print_exc()
    except Exception as e:
        fail("Unexpected error", str(e))
        traceback.print_exc()
    finally:
        # ── Step 7: Cleanup ───────────────────────────────────────────────
        print("STEP 7: Cleanup test users")
        cleanup_users()
        print()

    # ── Summary ───────────────────────────────────────────────────────────
    print("=" * 72)
    print(f"RESULTS:  {passed} passed,  {failed} failed")
    if errors:
        print("\nFailed checks:")
        for e in errors:
            print(f"  {e}")
    print("=" * 72)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
