"""
Seed script to create a demo user with comprehensive portfolio data.
Creates assets across ALL asset types, accounts, transactions, snapshots,
expenses, and alerts — enough to demo every feature of PortAct.

Usage: cd backend && python seed_demo_user.py

Demo credentials: demouser@portact.com / portact1
"""
import sys
import os
import random
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date, timedelta, timezone
import bcrypt
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import (
    User, Asset, AssetType, Transaction, TransactionType,
    Alert, AlertSeverity, AlertType,
    BankAccount, BankType, DematAccount, CryptoAccount,
    ExpenseCategory, Expense, ExpenseType, PaymentMethod,
    PortfolioSnapshot, AssetSnapshot,
    Portfolio, MutualFundHolding,
)
from app.models.demat_account import AccountMarket


def hash_password(password: str) -> str:
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def seed_demo_user():
    db: Session = SessionLocal()
    try:
        # ── Idempotency: delete existing demo user (cascade deletes everything) ──
        existing = db.query(User).filter(User.email == "demouser@portact.com").first()
        if existing:
            print("Demo user already exists. Deleting and re-creating...")
            # Delete all user data in dependency order using raw SQL.
            # ORM cascade doesn't match DB-level FK constraints, so we
            # handle the teardown explicitly to avoid integrity errors.
            uid = existing.id
            db.execute(text("DELETE FROM asset_snapshots WHERE portfolio_snapshot_id IN (SELECT id FROM portfolio_snapshots WHERE user_id = :uid)"), {"uid": uid})
            db.execute(text("DELETE FROM portfolio_snapshots WHERE user_id = :uid"), {"uid": uid})
            db.execute(text("DELETE FROM mutual_fund_holdings WHERE user_id = :uid"), {"uid": uid})
            db.execute(text("DELETE FROM transactions WHERE asset_id IN (SELECT id FROM assets WHERE user_id = :uid)"), {"uid": uid})
            db.execute(text("DELETE FROM alerts WHERE user_id = :uid"), {"uid": uid})
            db.execute(text("DELETE FROM expenses WHERE user_id = :uid"), {"uid": uid})
            db.execute(text("DELETE FROM expense_categories WHERE user_id = :uid"), {"uid": uid})
            db.execute(text("DELETE FROM assets WHERE user_id = :uid"), {"uid": uid})
            db.execute(text("DELETE FROM bank_accounts WHERE user_id = :uid"), {"uid": uid})
            db.execute(text("DELETE FROM demat_accounts WHERE user_id = :uid"), {"uid": uid})
            db.execute(text("DELETE FROM crypto_accounts WHERE user_id = :uid"), {"uid": uid})
            db.execute(text("DELETE FROM portfolios WHERE user_id = :uid"), {"uid": uid})
            db.execute(text("DELETE FROM statements WHERE user_id = :uid"), {"uid": uid})
            db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": uid})
            db.commit()

        # ══════════════════════════════════════════════════════════════════════════
        # 1. CREATE DEMO USER
        # ══════════════════════════════════════════════════════════════════════════
        print("Creating demo user...")
        user = User(
            email="demouser@portact.com",
            username="demouser",
            hashed_password=hash_password("portact1"),
            full_name="Rahul Sharma",
            is_active=True,
            is_superuser=False,
            phone="9876543210",
            date_of_birth=date(1990, 5, 15),
            gender="Male",
            address="42, MG Road, Indiranagar",
            city="Bangalore",
            state="Karnataka",
            pincode="560038",
            is_employed=True,
            basic_salary=125000.0,
            da_percentage=0,
            employer_name="TechVista Solutions Pvt Ltd",
            date_of_joining=date(2018, 7, 1),
            pf_employee_pct=12,
            pf_employer_pct=12,
        )
        db.add(user)
        db.flush()  # Get user.id
        user_id = user.id
        print(f"  User created (id={user_id})")

        # ══════════════════════════════════════════════════════════════════════════
        # 1b. CREATE DEFAULT PORTFOLIO
        # ══════════════════════════════════════════════════════════════════════════
        print("Creating default portfolio...")
        portfolio = Portfolio(
            user_id=user_id,
            name="Default",
            is_default=True,
            is_active=True,
        )
        db.add(portfolio)
        db.flush()
        portfolio_id = portfolio.id
        print(f"  Default portfolio created (id={portfolio_id})")

        # ── Second portfolio: Retirement ──
        retirement_portfolio = Portfolio(
            user_id=user_id,
            name="Retirement",
            description="Long-term retirement savings and pension investments",
            is_default=False,
            is_active=True,
        )
        db.add(retirement_portfolio)
        db.flush()
        retirement_portfolio_id = retirement_portfolio.id
        print(f"  Retirement portfolio created (id={retirement_portfolio_id})")

        # ══════════════════════════════════════════════════════════════════════════
        # 2. BANK ACCOUNTS
        # ══════════════════════════════════════════════════════════════════════════
        print("Creating bank accounts...")
        ba_icici = BankAccount(
            user_id=user_id, portfolio_id=portfolio_id,
            bank_name="icici_bank", account_type=BankType.SAVINGS,
            account_number="XXXX1234", account_holder_name="Rahul Sharma",
            ifsc_code="ICIC0001234", branch_name="Indiranagar Branch",
            current_balance=250000.0, is_active=True, is_primary=True,
            nickname="ICICI Salary Account",
        )
        ba_hdfc = BankAccount(
            user_id=user_id, portfolio_id=portfolio_id,
            bank_name="hdfc_bank", account_type=BankType.SAVINGS,
            account_number="XXXX5678", account_holder_name="Rahul Sharma",
            ifsc_code="HDFC0005678", branch_name="Koramangala Branch",
            current_balance=185000.0, is_active=True,
            nickname="HDFC Savings",
        )
        ba_sbi = BankAccount(
            user_id=user_id, portfolio_id=portfolio_id,
            bank_name="state_bank_of_india", account_type=BankType.CREDIT_CARD,
            account_number="XXXX9012", account_holder_name="Rahul Sharma",
            current_balance=42000.0, credit_limit=200000.0, available_balance=158000.0,
            is_active=True, nickname="SBI Credit Card",
        )
        ba_axis = BankAccount(
            user_id=user_id, portfolio_id=portfolio_id,
            bank_name="axis_bank", account_type=BankType.CURRENT,
            account_number="XXXX3456", account_holder_name="Rahul Sharma",
            ifsc_code="UTIB0003456", branch_name="HSR Layout Branch",
            current_balance=525000.0, is_active=True,
            nickname="Axis Current Account",
        )
        db.add_all([ba_icici, ba_hdfc, ba_sbi, ba_axis])
        db.flush()
        print(f"  4 bank accounts created")

        # ══════════════════════════════════════════════════════════════════════════
        # 3. DEMAT ACCOUNTS
        # ══════════════════════════════════════════════════════════════════════════
        print("Creating demat accounts...")
        da_zerodha = DematAccount(
            user_id=user_id, portfolio_id=portfolio_id,
            broker_name="zerodha",
            account_market=AccountMarket.DOMESTIC,
            account_id="ZR1234", account_holder_name="Rahul Sharma",
            demat_account_number="1208160012345678",
            cash_balance=15000.0, currency="INR",
            is_active=True, is_primary=True,
            nickname="Zerodha Trading",
        )
        da_groww = DematAccount(
            user_id=user_id, portfolio_id=portfolio_id,
            broker_name="groww",
            account_market=AccountMarket.DOMESTIC,
            account_id="GW5678", account_holder_name="Rahul Sharma",
            cash_balance=8000.0, currency="INR",
            is_active=True, nickname="Groww MF Account",
        )
        da_indmoney = DematAccount(
            user_id=user_id, portfolio_id=portfolio_id,
            broker_name="indmoney",
            account_market=AccountMarket.INTERNATIONAL,
            account_id="IM9012", account_holder_name="Rahul Sharma",
            cash_balance_usd=250.0, currency="USD",
            is_active=True, nickname="INDmoney US Stocks",
        )
        db.add_all([da_zerodha, da_groww, da_indmoney])
        db.flush()
        print(f"  3 demat accounts created")

        # ══════════════════════════════════════════════════════════════════════════
        # 4. CRYPTO ACCOUNTS
        # ══════════════════════════════════════════════════════════════════════════
        print("Creating crypto accounts...")
        ca_binance = CryptoAccount(
            user_id=user_id, portfolio_id=portfolio_id,
            exchange_name="binance",
            account_id="binance_rahul_01", account_holder_name="Rahul Sharma",
            cash_balance_usd=120.0, total_value_usd=4920.0,
            is_active=True, is_primary=True,
            nickname="Binance Main",
        )
        ca_wazirx = CryptoAccount(
            user_id=user_id, portfolio_id=portfolio_id,
            exchange_name="wazirx",
            account_id="wazirx_rahul_01", account_holder_name="Rahul Sharma",
            cash_balance_usd=85.0, total_value_usd=505.0,
            is_active=True, nickname="WazirX",
        )
        db.add_all([ca_binance, ca_wazirx])
        db.flush()
        print(f"  2 crypto accounts created")

        # ══════════════════════════════════════════════════════════════════════════
        # 5. ASSETS — ALL TYPES
        # ══════════════════════════════════════════════════════════════════════════
        print("Creating assets...")
        today = date.today()
        now = datetime.now(timezone.utc)
        all_assets = []

        def make_asset(**kwargs):
            """Helper to create an asset with calculated metrics."""
            invested = kwargs.get("total_invested", 0)
            current = kwargs.get("current_value", 0)
            pl = current - invested
            pl_pct = (pl / invested * 100) if invested > 0 else 0
            kwargs.setdefault("profit_loss", round(pl, 2))
            kwargs.setdefault("profit_loss_percentage", round(pl_pct, 2))
            kwargs.setdefault("is_active", True)
            kwargs.setdefault("user_id", user_id)
            kwargs.setdefault("portfolio_id", portfolio_id)
            asset = Asset(**kwargs)
            all_assets.append(asset)
            return asset

        # ── 5a. Indian Stocks (6) — Zerodha ─────────────────────────────────────
        stocks_data = [
            ("Reliance Industries", "RELIANCE", "RELIANCE.BSE", "INE002A01018", 50, 2400.0, 2900.0, 120000, 145000, "zerodha", {"exchange": "NSE", "sector": "Oil & Gas", "market_cap": "Large"}),
            ("TCS", "TCS", "TCS.BSE", "INE467B01029", 25, 3400.0, 3680.0, 85000, 92000, "zerodha", {"exchange": "NSE", "sector": "IT", "market_cap": "Large"}),
            ("HDFC Bank", "HDFCBANK", "HDFCBANK.BSE", "INE040A01034", 70, 1571.0, 1786.0, 110000, 125000, "zerodha", {"exchange": "NSE", "sector": "Banking", "market_cap": "Large"}),
            ("Infosys", "INFY", "INFY.BSE", "INE009A01021", 50, 1500.0, 1400.0, 75000, 70000, "zerodha", {"exchange": "NSE", "sector": "IT", "market_cap": "Large"}),
            ("ITC", "ITC", "ITC.BSE", "INE154A01025", 100, 450.0, 520.0, 45000, 52000, "zerodha", {"exchange": "NSE", "sector": "FMCG", "market_cap": "Large"}),
            ("Asian Paints", "ASIANPAINT", "ASIANPAINT.BSE", "INE021A01026", 20, 3000.0, 2750.0, 60000, 55000, "zerodha", {"exchange": "NSE", "sector": "Paints", "market_cap": "Large"}),
        ]
        for name, sym, api_sym, isin, qty, pp, cp, invested, current, broker, details in stocks_data:
            make_asset(
                asset_type=AssetType.STOCK, name=name, symbol=sym, api_symbol=api_sym,
                isin=isin, quantity=qty, purchase_price=pp, current_price=cp,
                total_invested=invested, current_value=current,
                demat_account_id=da_zerodha.id, broker_name=broker,
                account_holder_name="Rahul Sharma",
                purchase_date=now - timedelta(days=random.randint(180, 730)),
                details=details,
            )

        # ── 5b. US Stocks (3) — INDmoney ────────────────────────────────────────
        us_stocks_data = [
            ("Apple Inc", "AAPL", "AAPL", 30, 166.67, 206.67, 5000, 6200, {"exchange": "NASDAQ", "sector": "Technology", "market_cap": "Mega"}),
            ("Tesla Inc", "TSLA", "TSLA", 10, 300.0, 280.0, 3000, 2800, {"exchange": "NASDAQ", "sector": "Automotive", "market_cap": "Large"}),
            ("Microsoft Corp", "MSFT", "MSFT", 12, 375.0, 425.0, 4500, 5100, {"exchange": "NASDAQ", "sector": "Technology", "market_cap": "Mega"}),
        ]
        for name, sym, api_sym, qty, pp, cp, invested, current, details in us_stocks_data:
            make_asset(
                asset_type=AssetType.US_STOCK, name=name, symbol=sym, api_symbol=api_sym,
                quantity=qty, purchase_price=pp, current_price=cp,
                total_invested=invested, current_value=current,
                demat_account_id=da_indmoney.id, broker_name="indmoney",
                account_holder_name="Rahul Sharma",
                purchase_date=now - timedelta(days=random.randint(90, 365)),
                details=details,
            )

        # ── 5c. Equity Mutual Funds (3) — Groww ─────────────────────────────────
        eq_mf_data = [
            ("Parag Parikh Flexi Cap Fund", "PPFAS", "122639", "INF879O01027", 4200, 47.62, 58.33, 200000, 245000),
            ("Mirae Asset Large Cap Fund", "MIRAE_LC", "118834", "INF769K01EL5", 6500, 23.08, 26.46, 150000, 172000),
            ("SBI Small Cap Fund", "SBI_SC", "125497", "INF200K01RQ0", 8000, 12.50, 16.88, 100000, 135000),
        ]
        for name, sym, api_sym, isin, qty, pp, cp, invested, current in eq_mf_data:
            make_asset(
                asset_type=AssetType.EQUITY_MUTUAL_FUND, name=name, symbol=sym,
                api_symbol=api_sym, isin=isin,
                quantity=qty, purchase_price=pp, current_price=cp,
                total_invested=invested, current_value=current,
                demat_account_id=da_groww.id, broker_name="groww",
                account_holder_name="Rahul Sharma",
                purchase_date=now - timedelta(days=random.randint(365, 1095)),
                details={"fund_house": name.split()[0], "category": "Equity", "plan": "Direct Growth"},
            )

        # ── 5d. Debt Mutual Fund (1) ────────────────────────────────────────────
        make_asset(
            asset_type=AssetType.DEBT_MUTUAL_FUND,
            name="HDFC Corporate Bond Fund", symbol="HDFC_CB", api_symbol="119065",
            isin="INF179K01CF5", quantity=10000, purchase_price=30.0, current_price=31.8,
            total_invested=300000, current_value=318000,
            broker_name="groww", account_holder_name="Rahul Sharma",
            purchase_date=now - timedelta(days=540),
            details={"fund_house": "HDFC", "category": "Debt", "plan": "Direct Growth"},
        )

        # ── 5d2. Hybrid Mutual Fund (1) ───────────────────────────────────────
        make_asset(
            asset_type=AssetType.HYBRID_MUTUAL_FUND,
            name="ICICI Prudential Balanced Advantage Fund", symbol="ICICI_BAF",
            api_symbol="120242", isin="INF109K01BD0",
            quantity=5000, purchase_price=52.0, current_price=60.8,
            total_invested=260000, current_value=304000,
            demat_account_id=da_groww.id, broker_name="groww",
            account_holder_name="Rahul Sharma",
            purchase_date=now - timedelta(days=700),
            details={"fund_house": "ICICI Prudential", "category": "Hybrid",
                     "sub_category": "Balanced Advantage", "plan": "Direct Growth"},
        )

        # ── 5e. Commodities (2) ─────────────────────────────────────────────────
        make_asset(
            asset_type=AssetType.COMMODITY,
            name="Gold (24K)", symbol="GOLD", api_symbol="GOLD",
            quantity=35, purchase_price=7142.86, current_price=8857.14,
            total_invested=250000, current_value=310000,
            purchase_date=now - timedelta(days=900),
            details={"purity": "24K", "form": "Digital Gold", "unit": "grams"},
        )
        make_asset(
            asset_type=AssetType.COMMODITY,
            name="Silver", symbol="SILVER", api_symbol="SILVER",
            quantity=500, purchase_price=100.0, current_price=116.0,
            total_invested=50000, current_value=58000,
            purchase_date=now - timedelta(days=600),
            details={"purity": "999", "form": "Digital Silver", "unit": "grams"},
        )

        # ── 5f. Crypto (3) — Binance & WazirX ───────────────────────────────────
        make_asset(
            asset_type=AssetType.CRYPTO,
            name="Bitcoin (BTC)", symbol="BTC", api_symbol="bitcoin",
            quantity=0.025, purchase_price=80000.0, current_price=112000.0,
            total_invested=2000, current_value=2800,
            crypto_account_id=ca_binance.id,
            purchase_date=now - timedelta(days=365),
            details={"blockchain": "Bitcoin", "network": "Mainnet"},
        )
        make_asset(
            asset_type=AssetType.CRYPTO,
            name="Ethereum (ETH)", symbol="ETH", api_symbol="ethereum",
            quantity=0.5, purchase_price=3000.0, current_price=3800.0,
            total_invested=1500, current_value=1900,
            crypto_account_id=ca_binance.id,
            purchase_date=now - timedelta(days=300),
            details={"blockchain": "Ethereum", "network": "Mainnet"},
        )
        make_asset(
            asset_type=AssetType.CRYPTO,
            name="Solana (SOL)", symbol="SOL", api_symbol="solana",
            quantity=3.0, purchase_price=166.67, current_price=140.0,
            total_invested=500, current_value=420,
            crypto_account_id=ca_wazirx.id,
            purchase_date=now - timedelta(days=200),
            details={"blockchain": "Solana", "network": "Mainnet"},
        )

        # ── 5g. Sovereign Gold Bond (1) ──────────────────────────────────────────
        make_asset(
            asset_type=AssetType.SOVEREIGN_GOLD_BOND,
            name="SGB 2023-24 Series I", symbol="SGB2023I",
            quantity=15, purchase_price=6667.0, current_price=8133.0,
            total_invested=100000, current_value=122000,
            purchase_date=now - timedelta(days=450),
            details={"series": "2023-24 Series I", "issue_date": "2023-06-19",
                     "maturity_date": "2031-06-19", "coupon_rate": 2.5,
                     "grams_per_unit": 1},
        )

        # ── 5h. Bonds (3) ───────────────────────────────────────────────────────
        make_asset(
            asset_type=AssetType.CORPORATE_BOND,
            name="HDFC Corp Bond 8.5% 2027", symbol="HDFC-BOND",
            quantity=20, purchase_price=10000.0, current_price=10400.0,
            total_invested=200000, current_value=208000,
            purchase_date=now - timedelta(days=365),
            details={"issuer": "HDFC Ltd", "coupon_rate": 8.5, "face_value": 10000,
                     "maturity_date": "2027-03-15", "credit_rating": "AAA"},
        )
        make_asset(
            asset_type=AssetType.RBI_BOND,
            name="RBI Floating Rate Bond 2028", symbol="RBI-FRB",
            quantity=15, purchase_price=10000.0, current_price=10400.0,
            total_invested=150000, current_value=156000,
            purchase_date=now - timedelta(days=500),
            details={"coupon_rate": 8.05, "face_value": 10000,
                     "maturity_date": "2028-01-01", "interest_frequency": "Semi-Annual"},
        )
        make_asset(
            asset_type=AssetType.TAX_SAVING_BOND,
            name="NHAI Tax Free Bond 7.2% 2033", symbol="NHAI-TF",
            quantity=10, purchase_price=10000.0, current_price=10400.0,
            total_invested=100000, current_value=104000,
            purchase_date=now - timedelta(days=800),
            details={"issuer": "NHAI", "coupon_rate": 7.2, "face_value": 10000,
                     "maturity_date": "2033-02-01", "tax_free": True},
        )

        # ── 5i. REIT & InvIT (2) ────────────────────────────────────────────────
        make_asset(
            asset_type=AssetType.REIT,
            name="Embassy Office Parks REIT", symbol="EMBASSY", api_symbol="EMBASSY.BSE",
            isin="INE041025011", quantity=400, purchase_price=375.0, current_price=405.0,
            total_invested=150000, current_value=162000,
            demat_account_id=da_zerodha.id, broker_name="zerodha",
            purchase_date=now - timedelta(days=270),
            details={"dividend_yield": 6.8, "property_type": "Commercial Office",
                     "locations": "Bangalore, Mumbai, Pune"},
        )
        make_asset(
            asset_type=AssetType.INVIT,
            name="India Grid Trust InvIT", symbol="INDIGRID", api_symbol="INDIGRID.BSE",
            isin="INE219X23016", quantity=500, purchase_price=150.0, current_price=160.0,
            total_invested=75000, current_value=80000,
            demat_account_id=da_zerodha.id, broker_name="zerodha",
            purchase_date=now - timedelta(days=180),
            details={"dividend_yield": 12.0, "asset_type": "Power Transmission"},
        )

        # ── 5j. Post Office Schemes (4) ─────────────────────────────────────────
        make_asset(
            asset_type=AssetType.NSC,
            name="National Savings Certificate", symbol="NSC",
            quantity=1, purchase_price=100000.0, current_price=112000.0,
            total_invested=100000, current_value=112000,
            purchase_date=now - timedelta(days=730),
            details={"certificate_number": "NSC-2024-001234", "interest_rate": 7.7,
                     "maturity_date": (today + timedelta(days=1095)).isoformat(),
                     "compounding": "Annual", "lock_in_years": 5},
        )
        make_asset(
            asset_type=AssetType.KVP,
            name="Kisan Vikas Patra", symbol="KVP",
            quantity=1, purchase_price=50000.0, current_price=58000.0,
            total_invested=50000, current_value=58000,
            purchase_date=now - timedelta(days=900),
            details={"certificate_number": "KVP-2023-005678", "interest_rate": 7.5,
                     "maturity_date": (today + timedelta(days=2190)).isoformat(),
                     "doubling_period_months": 115},
        )
        make_asset(
            asset_type=AssetType.SCSS,
            name="Senior Citizen Savings Scheme", symbol="SCSS",
            quantity=1, purchase_price=500000.0, current_price=540000.0,
            total_invested=500000, current_value=540000,
            purchase_date=now - timedelta(days=365),
            details={"account_number": "SCSS-PO-9876", "interest_rate": 8.2,
                     "maturity_date": (today + timedelta(days=1460)).isoformat(),
                     "interest_frequency": "Quarterly", "post_office": "Indiranagar HPO"},
        )
        make_asset(
            asset_type=AssetType.MIS,
            name="Post Office Monthly Income Scheme", symbol="POMIS",
            quantity=1, purchase_price=450000.0, current_price=450000.0,
            total_invested=450000, current_value=450000,
            purchase_date=now - timedelta(days=200),
            details={"account_number": "MIS-PO-5432", "interest_rate": 7.4,
                     "maturity_date": (today + timedelta(days=1625)).isoformat(),
                     "monthly_payout": 2775, "post_office": "Koramangala HPO"},
        )

        # ── 5k. Government Schemes (5) ──────────────────────────────────────────
        make_asset(
            asset_type=AssetType.PPF,
            name="Public Provident Fund", symbol="PPF",
            quantity=1, purchase_price=1200000.0, current_price=1580000.0,
            total_invested=1200000, current_value=1580000,
            purchase_date=now - timedelta(days=2555),  # ~7 years
            details={"account_number": "PPF-SBI-12345678", "interest_rate": 7.1,
                     "maturity_date": (today + timedelta(days=2920)).isoformat(),
                     "opening_date": (today - timedelta(days=2555)).isoformat(),
                     "bank": "State Bank of India", "yearly_contribution": 150000},
        )
        make_asset(
            asset_type=AssetType.PF,
            name="Employee Provident Fund", symbol="EPF",
            quantity=1, purchase_price=850000.0, current_price=1020000.0,
            total_invested=850000, current_value=1020000,
            purchase_date=now - timedelta(days=2555),
            details={"uan_number": "100987654321", "interest_rate": 8.25,
                     "employer_name": "TechVista Solutions Pvt Ltd",
                     "employee_contribution_pct": 12, "employer_contribution_pct": 12,
                     "monthly_employee_contribution": 15000,
                     "monthly_employer_contribution": 15000},
        )
        make_asset(
            asset_type=AssetType.NPS,
            name="National Pension System - Tier I", symbol="NPS",
            quantity=1, purchase_price=400000.0, current_price=485000.0,
            total_invested=400000, current_value=485000,
            purchase_date=now - timedelta(days=1460),
            details={"pran_number": "1101234567890", "tier": "Tier I",
                     "fund_manager": "SBI Pension Funds",
                     "asset_allocation": {"equity": 75, "corporate_bonds": 15, "govt_bonds": 10},
                     "yearly_contribution": 50000},
        )
        make_asset(
            asset_type=AssetType.SSY,
            name="Sukanya Samriddhi Yojana", symbol="SSY",
            quantity=1, purchase_price=300000.0, current_price=365000.0,
            total_invested=300000, current_value=365000,
            purchase_date=now - timedelta(days=1825),
            details={"account_number": "SSY-PO-6789", "interest_rate": 8.2,
                     "beneficiary_name": "Ananya Sharma",
                     "beneficiary_dob": "2019-03-12",
                     "maturity_date": (today + timedelta(days=5475)).isoformat(),
                     "yearly_contribution": 50000,
                     "post_office": "Indiranagar HPO"},
        )
        make_asset(
            asset_type=AssetType.GRATUITY,
            name="Gratuity", symbol="GRATUITY",
            quantity=1, purchase_price=250000.0, current_price=250000.0,
            total_invested=250000, current_value=250000,
            details={"employer_name": "TechVista Solutions Pvt Ltd",
                     "years_of_service": 7, "last_drawn_salary": 125000,
                     "formula": "(15 * last_salary * years) / 26"},
        )

        # ── 5l. Insurance (2) ───────────────────────────────────────────────────
        make_asset(
            asset_type=AssetType.INSURANCE_POLICY,
            name="LIC Jeevan Anand", symbol="LIC-JA",
            quantity=1, purchase_price=500000.0, current_price=620000.0,
            total_invested=500000, current_value=620000,
            purchase_date=now - timedelta(days=2190),
            details={"policy_number": "LIC-4567890123", "policy_type": "Endowment",
                     "sum_assured": 2500000, "premium_amount": 50000,
                     "premium_frequency": "Annual", "maturity_date": "2038-06-15",
                     "nominee": "Priya Sharma", "insurer": "LIC of India"},
        )
        make_asset(
            asset_type=AssetType.INSURANCE_POLICY,
            name="HDFC Life Click 2 Protect", symbol="HDFC-C2P",
            quantity=1, purchase_price=25000.0, current_price=25000.0,
            total_invested=25000, current_value=25000,
            purchase_date=now - timedelta(days=730),
            details={"policy_number": "HDFC-7890123456", "policy_type": "Term",
                     "sum_assured": 10000000, "premium_amount": 12500,
                     "premium_frequency": "Annual", "maturity_date": "2054-05-15",
                     "nominee": "Priya Sharma", "insurer": "HDFC Life"},
        )

        # ── 5m. Fixed Deposits & Recurring Deposit (3) ──────────────────────────
        make_asset(
            asset_type=AssetType.FIXED_DEPOSIT,
            name="HDFC Bank FD 7.25%", symbol="HDFC-FD",
            quantity=1, purchase_price=500000.0, current_price=536000.0,
            total_invested=500000, current_value=536000,
            purchase_date=now - timedelta(days=365),
            details={"bank_name": "HDFC Bank", "interest_rate": 7.25,
                     "maturity_date": (today + timedelta(days=365)).isoformat(),
                     "tenure_months": 24, "interest_frequency": "Quarterly",
                     "fd_number": "FD-HDFC-001234"},
        )
        make_asset(
            asset_type=AssetType.FIXED_DEPOSIT,
            name="ICICI Bank FD 6.9%", symbol="ICICI-FD",
            quantity=1, purchase_price=300000.0, current_price=315000.0,
            total_invested=300000, current_value=315000,
            purchase_date=now - timedelta(days=270),
            details={"bank_name": "ICICI Bank", "interest_rate": 6.9,
                     "maturity_date": (today + timedelta(days=460)).isoformat(),
                     "tenure_months": 24, "interest_frequency": "Monthly",
                     "fd_number": "FD-ICICI-005678"},
        )
        make_asset(
            asset_type=AssetType.RECURRING_DEPOSIT,
            name="SBI RD Monthly 10K", symbol="SBI-RD",
            quantity=1, purchase_price=120000.0, current_price=126000.0,
            total_invested=120000, current_value=126000,
            purchase_date=now - timedelta(days=365),
            details={"bank_name": "SBI", "interest_rate": 6.5,
                     "maturity_date": (today + timedelta(days=365)).isoformat(),
                     "tenure_months": 24, "monthly_installment": 10000,
                     "rd_number": "RD-SBI-009012"},
        )

        # ── 5n. Real Estate (2) ─────────────────────────────────────────────────
        make_asset(
            asset_type=AssetType.REAL_ESTATE,
            name="2BHK Apartment, Whitefield, Bangalore",
            quantity=1, purchase_price=6500000.0, current_price=8200000.0,
            total_invested=6500000, current_value=8200000,
            purchase_date=now - timedelta(days=1825),
            details={"property_type": "house", "area": 1150, "area_unit": "sqft",
                     "property_address": "Prestige Shantiniketan, Whitefield, Bangalore 560066",
                     "location": "Whitefield, Bangalore",
                     "purchase_price": 6500000.0, "current_market_value": 8200000.0,
                     "registration_date": (today - timedelta(days=1825)).isoformat(),
                     "carpet_area_sqft": 950, "floor": 12, "total_floors": 25,
                     "facing": "East", "furnishing": "Semi-Furnished"},
        )
        make_asset(
            asset_type=AssetType.REAL_ESTATE,
            name="Plot, Electronic City, Bangalore",
            quantity=1, purchase_price=2500000.0, current_price=3500000.0,
            total_invested=2500000, current_value=3500000,
            purchase_date=now - timedelta(days=1095),
            details={"property_type": "land", "area": 2400, "area_unit": "sqft",
                     "property_address": "BDA Layout, Electronic City Phase 2, Bangalore 560100",
                     "location": "Electronic City, Bangalore",
                     "purchase_price": 2500000.0, "current_market_value": 3500000.0,
                     "registration_date": (today - timedelta(days=1095)).isoformat(),
                     "dimensions": "40x60 ft", "facing": "North"},
        )

        # ── 5o. Cash (1) ────────────────────────────────────────────────────────
        make_asset(
            asset_type=AssetType.CASH,
            name="Cash in Hand",
            quantity=1, purchase_price=50000.0, current_price=50000.0,
            total_invested=50000, current_value=50000,
        )

        # ── 5p. ESOP (1) ──────────────────────────────────────────────────────
        make_asset(
            asset_type=AssetType.ESOP,
            name="TechVista Solutions ESOP", symbol="TECHVISTA-ESOP",
            quantity=500, purchase_price=120.0, current_price=185.0,
            total_invested=60000, current_value=92500,
            purchase_date=now - timedelta(days=1095),
            details={
                "company": "TechVista Solutions Pvt Ltd",
                "grant_date": (today - timedelta(days=1095)).isoformat(),
                "vesting_schedule": "25% per year over 4 years",
                "exercise_price": 120.0,
                "total_granted": 2000,
                "vested": 1500,
                "exercised": 500,
                "currency": "INR",
                "cliff_months": 12,
                "expiry_date": (today + timedelta(days=2555)).isoformat(),
            },
        )

        # ── 5q. RSU (1) ───────────────────────────────────────────────────────
        make_asset(
            asset_type=AssetType.RSU,
            name="Google RSU (Alphabet Inc)", symbol="GOOGL", api_symbol="GOOGL",
            quantity=8, purchase_price=0.0, current_price=178.0,
            total_invested=0, current_value=1424,
            demat_account_id=da_indmoney.id, broker_name="indmoney",
            account_holder_name="Rahul Sharma",
            purchase_date=now - timedelta(days=365),
            details={
                "company": "Alphabet Inc",
                "grant_date": (today - timedelta(days=730)).isoformat(),
                "vesting_schedule": "25% per year over 4 years",
                "total_granted": 32,
                "vested": 16,
                "released": 8,
                "currency": "USD",
                "price_usd": 178.0,
                "usd_to_inr_rate": 83.5,
            },
        )

        # ── 5r. Savings Account (1) ───────────────────────────────────────────
        make_asset(
            asset_type=AssetType.SAVINGS_ACCOUNT,
            name="ICICI Savings Account", symbol="ICICI-SAV",
            quantity=1, purchase_price=250000.0, current_price=250000.0,
            total_invested=250000, current_value=250000,
            details={
                "bank_name": "ICICI Bank",
                "account_number": "XXXX1234",
                "interest_rate": 3.0,
                "account_type": "Savings",
            },
        )

        # ══════════════════════════════════════════════════════════════════════════
        # 5.R  RETIREMENT PORTFOLIO ASSETS
        # ══════════════════════════════════════════════════════════════════════════
        print("Creating retirement portfolio assets...")
        retirement_assets_start = len(all_assets)

        # ── R1. Blue-chip Stocks (3) — Zerodha ─────────────────────────────────
        ret_stocks = [
            ("Bajaj Finance", "BAJFINANCE", "BAJFINANCE.BSE", "INE296A01024", 30, 6200.0, 7100.0, 186000, 213000, "zerodha", {"exchange": "NSE", "sector": "Finance", "market_cap": "Large"}),
            ("HUL", "HINDUNILVR", "HINDUNILVR.BSE", "INE030A01027", 60, 2200.0, 2500.0, 132000, 150000, "zerodha", {"exchange": "NSE", "sector": "FMCG", "market_cap": "Large"}),
            ("Kotak Mahindra Bank", "KOTAKBANK", "KOTAKBANK.BSE", "INE237A01028", 40, 1800.0, 1950.0, 72000, 78000, "zerodha", {"exchange": "NSE", "sector": "Banking", "market_cap": "Large"}),
        ]
        for name, sym, api_sym, isin, qty, pp, cp, invested, current, broker, details in ret_stocks:
            make_asset(
                asset_type=AssetType.STOCK, name=name, symbol=sym, api_symbol=api_sym,
                isin=isin, quantity=qty, purchase_price=pp, current_price=cp,
                total_invested=invested, current_value=current,
                demat_account_id=da_zerodha.id, broker_name=broker,
                account_holder_name="Rahul Sharma",
                purchase_date=now - timedelta(days=random.randint(365, 1095)),
                details=details,
                portfolio_id=retirement_portfolio_id,
            )

        # ── R2. Equity Mutual Fund (1) — Groww ─────────────────────────────────
        ret_mf = make_asset(
            asset_type=AssetType.EQUITY_MUTUAL_FUND,
            name="HDFC Flexi Cap Fund", symbol="HDFC_FC",
            api_symbol="119531", isin="INF179K01CA6",
            quantity=12000, purchase_price=16.67, current_price=20.83,
            total_invested=200000, current_value=250000,
            demat_account_id=da_groww.id, broker_name="groww",
            account_holder_name="Rahul Sharma",
            purchase_date=now - timedelta(days=random.randint(730, 1460)),
            details={"fund_house": "HDFC", "category": "Equity", "plan": "Direct Growth"},
            portfolio_id=retirement_portfolio_id,
        )

        # ── R3. Debt Mutual Fund (1) — Groww ──────────────────────────────────
        make_asset(
            asset_type=AssetType.DEBT_MUTUAL_FUND,
            name="SBI Magnum Gilt Fund", symbol="SBI_GILT",
            api_symbol="119455", isin="INF200K01677",
            quantity=5000, purchase_price=50.0, current_price=56.0,
            total_invested=250000, current_value=280000,
            broker_name="groww", account_holder_name="Rahul Sharma",
            purchase_date=now - timedelta(days=800),
            details={"fund_house": "SBI", "category": "Debt", "sub_category": "Gilt", "plan": "Direct Growth"},
            portfolio_id=retirement_portfolio_id,
        )

        # ── R4. NPS Tier II ───────────────────────────────────────────────────
        make_asset(
            asset_type=AssetType.NPS,
            name="National Pension System - Tier II", symbol="NPS-T2",
            quantity=1, purchase_price=150000.0, current_price=182000.0,
            total_invested=150000, current_value=182000,
            purchase_date=now - timedelta(days=730),
            details={"pran_number": "1101234567890", "tier": "Tier II",
                     "fund_manager": "HDFC Pension Management",
                     "asset_allocation": {"equity": 50, "corporate_bonds": 30, "govt_bonds": 20},
                     "yearly_contribution": 100000},
            portfolio_id=retirement_portfolio_id,
        )

        # ── R5. Fixed Deposit ─────────────────────────────────────────────────
        make_asset(
            asset_type=AssetType.FIXED_DEPOSIT,
            name="SBI FD 7.1% (Retirement)", symbol="SBI-FD-RET",
            quantity=1, purchase_price=1000000.0, current_price=1071000.0,
            total_invested=1000000, current_value=1071000,
            purchase_date=now - timedelta(days=365),
            details={"bank_name": "SBI", "interest_rate": 7.1,
                     "maturity_date": (today + timedelta(days=1095)).isoformat(),
                     "tenure_months": 48, "interest_frequency": "Quarterly",
                     "fd_number": "FD-SBI-RET-001"},
            portfolio_id=retirement_portfolio_id,
        )

        # ── R6. Sovereign Gold Bond ───────────────────────────────────────────
        make_asset(
            asset_type=AssetType.SOVEREIGN_GOLD_BOND,
            name="SGB 2024-25 Series II", symbol="SGB2024II",
            quantity=10, purchase_price=6800.0, current_price=8133.0,
            total_invested=68000, current_value=81330,
            purchase_date=now - timedelta(days=300),
            details={"series": "2024-25 Series II", "issue_date": "2024-09-15",
                     "maturity_date": "2032-09-15", "coupon_rate": 2.5,
                     "grams_per_unit": 1},
            portfolio_id=retirement_portfolio_id,
        )

        # ── R7. RBI Bond ─────────────────────────────────────────────────────
        make_asset(
            asset_type=AssetType.RBI_BOND,
            name="RBI Floating Rate Bond 2030", symbol="RBI-FRB-2030",
            quantity=10, purchase_price=10000.0, current_price=10350.0,
            total_invested=100000, current_value=103500,
            purchase_date=now - timedelta(days=400),
            details={"coupon_rate": 8.05, "face_value": 10000,
                     "maturity_date": "2030-07-01", "interest_frequency": "Semi-Annual"},
            portfolio_id=retirement_portfolio_id,
        )

        # ── R8. Insurance (1) ────────────────────────────────────────────────
        make_asset(
            asset_type=AssetType.INSURANCE_POLICY,
            name="ICICI Pru Retirement Plan", symbol="ICICI-RET",
            quantity=1, purchase_price=300000.0, current_price=380000.0,
            total_invested=300000, current_value=380000,
            purchase_date=now - timedelta(days=1825),
            details={"policy_number": "ICICI-RET-3456789", "policy_type": "Pension",
                     "sum_assured": 1500000, "premium_amount": 30000,
                     "premium_frequency": "Annual", "maturity_date": "2045-03-15",
                     "nominee": "Priya Sharma", "insurer": "ICICI Prudential Life"},
            portfolio_id=retirement_portfolio_id,
        )

        retirement_asset_count = len(all_assets) - retirement_assets_start
        print(f"  {retirement_asset_count} retirement portfolio assets created")

        db.add_all(all_assets)
        db.flush()
        print(f"  {len(all_assets)} total assets created")

        # ══════════════════════════════════════════════════════════════════════════
        # 5.5 MUTUAL FUND HOLDINGS (stock compositions)
        # ══════════════════════════════════════════════════════════════════════════
        print("Creating mutual fund holdings...")
        mf_holdings = []

        def find_asset(name):
            return next((a for a in all_assets if a.name == name), None)

        ppfas = find_asset("Parag Parikh Flexi Cap Fund")
        mirae = find_asset("Mirae Asset Large Cap Fund")
        sbi_sc = find_asset("SBI Small Cap Fund")
        hdfc_cb = find_asset("HDFC Corporate Bond Fund")
        icici_baf = find_asset("ICICI Prudential Balanced Advantage Fund")

        def add_mf_holdings(mf_asset, holdings_data):
            if not mf_asset:
                return
            for stock_name, symbol, isin, pct, sector, industry, mcap, price in holdings_data:
                hv = round(mf_asset.current_value * pct / 100, 2)
                qty = round(hv / price, 2) if price > 0 else 0
                mf_holdings.append(MutualFundHolding(
                    asset_id=mf_asset.id, user_id=user_id,
                    stock_name=stock_name, stock_symbol=symbol, isin=isin,
                    holding_percentage=pct, holding_value=hv, quantity_held=qty,
                    sector=sector, industry=industry, market_cap=mcap,
                    stock_current_price=price, data_source="seed",
                ))

        # Parag Parikh Flexi Cap Fund — top holdings
        add_mf_holdings(ppfas, [
            ("HDFC Bank Ltd", "HDFCBANK", "INE040A01034", 9.5, "Banking", "Private Bank", "Large", 1786.0),
            ("Bajaj Holdings & Investment", "BAJAJHLDNG", "INE118A01012", 5.8, "Finance", "Holding Company", "Large", 8500.0),
            ("ITC Ltd", "ITC", "INE154A01025", 5.2, "FMCG", "Tobacco", "Large", 520.0),
            ("Alphabet Inc (Google)", "GOOGL", "US02079K3059", 4.8, "Technology", "Internet", "Mega", 178.0),
            ("Microsoft Corp", "MSFT", "US5949181045", 4.2, "Technology", "Software", "Mega", 425.0),
            ("Amazon.com Inc", "AMZN", "US0231351067", 3.5, "Technology", "E-Commerce", "Mega", 195.0),
            ("Meta Platforms Inc", "META", "US30303M1027", 3.1, "Technology", "Social Media", "Mega", 520.0),
            ("Power Grid Corp", "POWERGRID", "INE752E01010", 2.8, "Utilities", "Power", "Large", 320.0),
            ("Coal India Ltd", "COALINDIA", "INE522F01014", 2.5, "Mining", "Coal", "Large", 450.0),
            ("Maruti Suzuki India", "MARUTI", "INE585B01010", 2.3, "Automobile", "Cars", "Large", 12500.0),
        ])

        # Mirae Asset Large Cap Fund — top holdings
        add_mf_holdings(mirae, [
            ("HDFC Bank Ltd", "HDFCBANK", "INE040A01034", 10.2, "Banking", "Private Bank", "Large", 1786.0),
            ("ICICI Bank Ltd", "ICICIBANK", "INE090A01021", 8.5, "Banking", "Private Bank", "Large", 1250.0),
            ("Reliance Industries", "RELIANCE", "INE002A01018", 8.0, "Oil & Gas", "Conglomerate", "Large", 2900.0),
            ("Infosys Ltd", "INFY", "INE009A01021", 6.5, "IT", "Software", "Large", 1400.0),
            ("TCS Ltd", "TCS", "INE467B01029", 5.8, "IT", "Software", "Large", 3680.0),
            ("Larsen & Toubro", "LT", "INE018A01030", 5.0, "Infrastructure", "Engineering", "Large", 3500.0),
            ("Axis Bank Ltd", "AXISBANK", "INE238A01034", 4.2, "Banking", "Private Bank", "Large", 1180.0),
            ("SBI", "SBIN", "INE062A01020", 3.8, "Banking", "Public Bank", "Large", 820.0),
        ])

        # SBI Small Cap Fund — top holdings
        add_mf_holdings(sbi_sc, [
            ("Blue Star Ltd", "BLUESTARCO", "INE472A01039", 3.2, "Consumer Durables", "AC", "Small", 1650.0),
            ("Finolex Cables", "FINCABLES", "INE235A01022", 2.8, "Manufacturing", "Cables", "Small", 1150.0),
            ("Chalet Hotels", "CHALET", "INE427F01028", 2.5, "Hospitality", "Hotels", "Small", 850.0),
            ("IIFL Finance", "IIFL", "INE530B01024", 2.3, "Finance", "NBFC", "Small", 520.0),
            ("Praj Industries", "PRAJIND", "INE074A01025", 2.1, "Engineering", "Capital Goods", "Small", 680.0),
            ("Elgi Equipments", "ELGIEQUIP", "INE285A01027", 1.9, "Manufacturing", "Compressors", "Small", 580.0),
        ])

        # HDFC Corporate Bond Fund — top holdings (bonds)
        add_mf_holdings(hdfc_cb, [
            ("GOI 7.18% 2037", "GOI-2037", "IN0020220143", 12.0, "Government", "G-Sec", "Sovereign", 101.5),
            ("HDFC Bank NCD 7.95%", "HDFC-NCD", "INE040A08310", 8.5, "Banking", "NCD", "Large", 1025.0),
            ("REC Ltd NCD 7.54%", "REC-NCD", "INE020B08DR8", 6.2, "Power", "NCD", "Large", 1015.0),
            ("PFC Ltd NCD 7.65%", "PFC-NCD", "INE134E08LA0", 5.5, "Power", "NCD", "Large", 1020.0),
            ("NABARD Bond 7.40%", "NABARD", "INE261F08CW0", 4.8, "Development", "Bond", "Sovereign", 1010.0),
        ])

        # ICICI Prudential Balanced Advantage Fund — mixed holdings
        add_mf_holdings(icici_baf, [
            ("ICICI Bank Ltd", "ICICIBANK", "INE090A01021", 7.5, "Banking", "Private Bank", "Large", 1250.0),
            ("HDFC Bank Ltd", "HDFCBANK", "INE040A01034", 6.8, "Banking", "Private Bank", "Large", 1786.0),
            ("Reliance Industries", "RELIANCE", "INE002A01018", 5.5, "Oil & Gas", "Conglomerate", "Large", 2900.0),
            ("Infosys Ltd", "INFY", "INE009A01021", 4.2, "IT", "Software", "Large", 1400.0),
            ("GOI 7.26% 2033", "GOI-2033", "IN0020220028", 8.0, "Government", "G-Sec", "Sovereign", 102.0),
            ("NTPC Ltd", "NTPC", "INE733E01010", 3.5, "Power", "Utilities", "Large", 380.0),
            ("SBI", "SBIN", "INE062A01020", 3.0, "Banking", "Public Bank", "Large", 820.0),
        ])

        # HDFC Flexi Cap Fund (Retirement portfolio) — top holdings
        hdfc_fc = find_asset("HDFC Flexi Cap Fund")
        add_mf_holdings(hdfc_fc, [
            ("ICICI Bank Ltd", "ICICIBANK", "INE090A01021", 8.8, "Banking", "Private Bank", "Large", 1250.0),
            ("HDFC Bank Ltd", "HDFCBANK", "INE040A01034", 7.5, "Banking", "Private Bank", "Large", 1786.0),
            ("Bharti Airtel Ltd", "BHARTIARTL", "INE397D01024", 5.5, "Telecom", "Telecom Services", "Large", 1620.0),
            ("Larsen & Toubro", "LT", "INE018A01030", 4.8, "Infrastructure", "Engineering", "Large", 3500.0),
            ("SBI", "SBIN", "INE062A01020", 4.2, "Banking", "Public Bank", "Large", 820.0),
            ("Axis Bank Ltd", "AXISBANK", "INE238A01034", 3.9, "Banking", "Private Bank", "Large", 1180.0),
            ("Sun Pharma", "SUNPHARMA", "INE044A01036", 3.5, "Pharma", "Pharmaceuticals", "Large", 1750.0),
            ("Titan Company", "TITAN", "INE280A01028", 3.0, "Consumer", "Jewellery", "Large", 3250.0),
        ])

        db.add_all(mf_holdings)
        db.flush()
        print(f"  {len(mf_holdings)} mutual fund holdings created")

        # ══════════════════════════════════════════════════════════════════════════
        # 6. TRANSACTIONS
        # ══════════════════════════════════════════════════════════════════════════
        print("Creating transactions...")
        transactions = []
        for asset in all_assets:
            if asset.asset_type in (
                AssetType.STOCK, AssetType.US_STOCK, AssetType.EQUITY_MUTUAL_FUND,
                AssetType.DEBT_MUTUAL_FUND, AssetType.HYBRID_MUTUAL_FUND,
                AssetType.CRYPTO, AssetType.REIT,
                AssetType.INVIT, AssetType.COMMODITY, AssetType.SOVEREIGN_GOLD_BOND,
            ):
                # BUY transaction
                buy_date = asset.purchase_date or (now - timedelta(days=365))
                transactions.append(Transaction(
                    asset_id=asset.id,
                    transaction_type=TransactionType.BUY,
                    transaction_date=buy_date,
                    quantity=asset.quantity,
                    price_per_unit=asset.purchase_price,
                    total_amount=asset.total_invested,
                    fees=round(asset.total_invested * 0.001, 2),  # ~0.1% fees
                    description=f"Purchased {asset.quantity} units of {asset.name}",
                ))

                # DIVIDEND for some stocks
                if asset.asset_type == AssetType.STOCK and asset.name in ("Reliance Industries", "TCS", "ITC"):
                    transactions.append(Transaction(
                        asset_id=asset.id,
                        transaction_type=TransactionType.DIVIDEND,
                        transaction_date=now - timedelta(days=random.randint(30, 90)),
                        quantity=asset.quantity,
                        price_per_unit=0,
                        total_amount=round(asset.total_invested * 0.015, 2),  # ~1.5% dividend
                        description=f"Dividend received for {asset.name}",
                    ))

            elif asset.asset_type in (AssetType.ESOP, AssetType.RSU):
                # BONUS transaction for vesting
                transactions.append(Transaction(
                    asset_id=asset.id,
                    transaction_type=TransactionType.BONUS,
                    transaction_date=asset.purchase_date or (now - timedelta(days=365)),
                    quantity=asset.quantity,
                    price_per_unit=asset.current_price,
                    total_amount=asset.current_value,
                    description=f"Vested {asset.quantity} units of {asset.name}",
                ))

            elif asset.asset_type in (AssetType.FIXED_DEPOSIT, AssetType.RECURRING_DEPOSIT):
                # DEPOSIT transaction
                transactions.append(Transaction(
                    asset_id=asset.id,
                    transaction_type=TransactionType.DEPOSIT,
                    transaction_date=asset.purchase_date or (now - timedelta(days=365)),
                    quantity=1,
                    price_per_unit=asset.total_invested,
                    total_amount=asset.total_invested,
                    description=f"Opened {asset.name}",
                ))
                # INTEREST transaction
                transactions.append(Transaction(
                    asset_id=asset.id,
                    transaction_type=TransactionType.INTEREST,
                    transaction_date=now - timedelta(days=30),
                    quantity=1,
                    price_per_unit=0,
                    total_amount=asset.current_value - asset.total_invested,
                    description=f"Interest credited for {asset.name}",
                ))

        db.add_all(transactions)
        db.flush()
        print(f"  {len(transactions)} transactions created")

        # ══════════════════════════════════════════════════════════════════════════
        # 7. PORTFOLIO SNAPSHOTS (30 days)
        # ══════════════════════════════════════════════════════════════════════════
        print("Creating portfolio snapshots (30 days)...")
        snapshot_count = 0

        # Calculate final portfolio totals
        total_invested_final = sum(a.total_invested for a in all_assets)
        total_value_final = sum(a.current_value for a in all_assets)
        # Add bank balances
        bank_total = ba_icici.current_balance + ba_hdfc.current_balance + ba_axis.current_balance
        total_invested_final += bank_total
        total_value_final += bank_total

        for day_offset in range(30, 0, -1):
            snap_date = today - timedelta(days=day_offset)

            # Gradually approach current values (earlier days have lower values)
            progress = (30 - day_offset) / 30  # 0.0 → 1.0
            noise = random.uniform(-0.005, 0.005)  # ±0.5% daily noise

            # Portfolio starts at ~95% of final value and approaches 100%
            daily_factor = 0.95 + (0.05 * progress) + noise

            snap_invested = round(total_invested_final * (0.98 + 0.02 * progress), 2)
            snap_value = round(total_value_final * daily_factor, 2)
            snap_pl = round(snap_value - snap_invested, 2)
            snap_pl_pct = round((snap_pl / snap_invested * 100) if snap_invested > 0 else 0, 2)

            portfolio_snap = PortfolioSnapshot(
                user_id=user_id,
                snapshot_date=snap_date,
                total_invested=snap_invested,
                total_current_value=snap_value,
                total_profit_loss=snap_pl,
                total_profit_loss_percentage=snap_pl_pct,
                total_assets_count=len(all_assets),
            )
            db.add(portfolio_snap)
            db.flush()

            # Add asset snapshots for a subset of assets (top holdings)
            for asset in all_assets[:15]:  # Top 15 assets for snapshots
                asset_factor = 0.95 + (0.05 * progress) + random.uniform(-0.008, 0.008)
                a_value = round(asset.current_value * asset_factor, 2)
                a_invested = asset.total_invested
                a_pl = round(a_value - a_invested, 2)
                a_pl_pct = round((a_pl / a_invested * 100) if a_invested > 0 else 0, 2)

                db.add(AssetSnapshot(
                    portfolio_snapshot_id=portfolio_snap.id,
                    snapshot_date=snap_date,
                    snapshot_source="asset",
                    asset_id=asset.id,
                    asset_type=asset.asset_type.value,
                    asset_name=asset.name,
                    asset_symbol=asset.symbol,
                    quantity=asset.quantity,
                    purchase_price=asset.purchase_price,
                    current_price=round(asset.current_price * asset_factor, 2),
                    total_invested=a_invested,
                    current_value=a_value,
                    profit_loss=a_pl,
                    profit_loss_percentage=a_pl_pct,
                ))

            # Add bank account snapshots
            for ba, label in [(ba_icici, "ICICI Savings"), (ba_hdfc, "HDFC Savings"), (ba_axis, "Axis Current")]:
                bal = round(ba.current_balance * (0.97 + 0.03 * progress + random.uniform(-0.01, 0.01)), 2)
                db.add(AssetSnapshot(
                    portfolio_snapshot_id=portfolio_snap.id,
                    snapshot_date=snap_date,
                    snapshot_source="bank_account",
                    bank_account_id=ba.id,
                    asset_type=None,
                    asset_name=label,
                    asset_symbol=None,
                    quantity=1,
                    purchase_price=bal,
                    current_price=bal,
                    total_invested=bal,
                    current_value=bal,
                    profit_loss=0,
                    profit_loss_percentage=0,
                ))

            # Add demat cash snapshots
            for da, label in [(da_zerodha, "Zerodha - Cash"), (da_groww, "Groww - Cash")]:
                if da.cash_balance and da.cash_balance > 0:
                    bal = round(da.cash_balance * (0.97 + 0.03 * progress + random.uniform(-0.01, 0.01)), 2)
                    db.add(AssetSnapshot(
                        portfolio_snapshot_id=portfolio_snap.id,
                        snapshot_date=snap_date,
                        snapshot_source="demat_cash",
                        demat_account_id=da.id,
                        asset_type=None,
                        asset_name=label,
                        asset_symbol=None,
                        quantity=1,
                        purchase_price=bal,
                        current_price=bal,
                        total_invested=bal,
                        current_value=bal,
                        profit_loss=0,
                        profit_loss_percentage=0,
                    ))

            # Add crypto cash snapshots
            for ca, label in [(ca_binance, "Binance - Cash (USD)"), (ca_wazirx, "WazirX - Cash (USD)")]:
                if ca.cash_balance_usd and ca.cash_balance_usd > 0:
                    bal = round(ca.cash_balance_usd * (0.97 + 0.03 * progress + random.uniform(-0.01, 0.01)), 2)
                    db.add(AssetSnapshot(
                        portfolio_snapshot_id=portfolio_snap.id,
                        snapshot_date=snap_date,
                        snapshot_source="crypto_cash",
                        crypto_account_id=ca.id,
                        asset_type=None,
                        asset_name=label,
                        asset_symbol=None,
                        quantity=1,
                        purchase_price=bal,
                        current_price=bal,
                        total_invested=bal,
                        current_value=bal,
                        profit_loss=0,
                        profit_loss_percentage=0,
                    ))

            snapshot_count += 1

        print(f"  {snapshot_count} daily snapshots created")

        # ══════════════════════════════════════════════════════════════════════════
        # 8. EXPENSE CATEGORIES (for demo user)
        # ══════════════════════════════════════════════════════════════════════════
        print("Creating expense categories...")
        categories_data = [
            ("Groceries", "Food and household items", "🛒", "#4CAF50", False),
            ("Dining & Restaurants", "Eating out, restaurants, cafes", "🍽️", "#FF9800", False),
            ("Transportation", "Fuel, public transport, ride-sharing", "🚗", "#2196F3", False),
            ("Utilities", "Electricity, water, gas, internet", "💡", "#FFC107", False),
            ("Rent & Mortgage", "Housing payments", "🏠", "#9C27B0", False),
            ("Healthcare & Medical", "Doctor visits, medicines", "⚕️", "#F44336", False),
            ("Entertainment", "Movies, games, hobbies", "🎬", "#E91E63", False),
            ("Shopping & Clothing", "Clothes, accessories", "👕", "#673AB7", False),
            ("Education", "Tuition, books, courses", "📚", "#3F51B5", False),
            ("Subscriptions", "Monthly subscriptions", "📱", "#9E9E9E", False),
            ("Salary & Income", "Salary, wages, income", "💰", "#4CAF50", True),
            ("Investments & Returns", "Dividends, interest", "📈", "#009688", True),
        ]
        cat_map = {}
        for cat_name, desc, icon, color, is_income in categories_data:
            cat = ExpenseCategory(
                user_id=user_id, name=cat_name, description=desc,
                icon=icon, color=color, is_income=is_income,
                is_system=False, is_active=True,
            )
            db.add(cat)
            db.flush()
            cat_map[cat_name] = cat.id

        print(f"  {len(categories_data)} expense categories created")

        # ══════════════════════════════════════════════════════════════════════════
        # 9. SAMPLE EXPENSES
        # ══════════════════════════════════════════════════════════════════════════
        print("Creating sample expenses...")
        expenses_data = [
            # (days_ago, type, amount, description, category, bank_account, payment_method, merchant)
            (1, ExpenseType.DEBIT, 2450, "Swiggy order", "Dining & Restaurants", ba_icici, PaymentMethod.UPI, "Swiggy"),
            (2, ExpenseType.DEBIT, 4200, "More Supermarket", "Groceries", ba_icici, PaymentMethod.DEBIT_CARD, "More Supermarket"),
            (3, ExpenseType.DEBIT, 1500, "Netflix + Spotify", "Subscriptions", ba_hdfc, PaymentMethod.NET_BANKING, "Netflix"),
            (4, ExpenseType.DEBIT, 800, "Uber ride to office", "Transportation", ba_icici, PaymentMethod.UPI, "Uber"),
            (5, ExpenseType.DEBIT, 25000, "Rent payment", "Rent & Mortgage", ba_icici, PaymentMethod.NET_BANKING, "Landlord"),
            (6, ExpenseType.DEBIT, 3500, "Electricity bill - BESCOM", "Utilities", ba_hdfc, PaymentMethod.UPI, "BESCOM"),
            (7, ExpenseType.DEBIT, 1200, "Amazon Prime renewal", "Subscriptions", ba_sbi, PaymentMethod.CREDIT_CARD, "Amazon"),
            (8, ExpenseType.DEBIT, 6500, "Decathlon sports gear", "Shopping & Clothing", ba_sbi, PaymentMethod.CREDIT_CARD, "Decathlon"),
            (9, ExpenseType.CREDIT, 125000, "Salary - TechVista Solutions", "Salary & Income", ba_icici, PaymentMethod.NET_BANKING, "TechVista Solutions"),
            (10, ExpenseType.DEBIT, 2800, "Apollo Pharmacy", "Healthcare & Medical", ba_icici, PaymentMethod.UPI, "Apollo Pharmacy"),
            (12, ExpenseType.DEBIT, 3200, "BigBasket grocery", "Groceries", ba_icici, PaymentMethod.UPI, "BigBasket"),
            (13, ExpenseType.DEBIT, 950, "Ola ride", "Transportation", ba_hdfc, PaymentMethod.UPI, "Ola"),
            (15, ExpenseType.DEBIT, 4500, "PVR movie + dinner", "Entertainment", ba_sbi, PaymentMethod.CREDIT_CARD, "PVR Cinemas"),
            (17, ExpenseType.DEBIT, 2100, "Jio broadband", "Utilities", ba_hdfc, PaymentMethod.NET_BANKING, "Jio"),
            (18, ExpenseType.DEBIT, 1800, "Zomato orders", "Dining & Restaurants", ba_icici, PaymentMethod.UPI, "Zomato"),
            (20, ExpenseType.DEBIT, 15000, "Udemy course bundle", "Education", ba_hdfc, PaymentMethod.DEBIT_CARD, "Udemy"),
            (22, ExpenseType.DEBIT, 3800, "DMart weekly grocery", "Groceries", ba_icici, PaymentMethod.UPI, "DMart"),
            (24, ExpenseType.CREDIT, 1800, "Reliance dividend", "Investments & Returns", ba_icici, PaymentMethod.NET_BANKING, "Reliance Industries"),
            (25, ExpenseType.DEBIT, 12000, "Myntra clothing", "Shopping & Clothing", ba_sbi, PaymentMethod.CREDIT_CARD, "Myntra"),
            (27, ExpenseType.DEBIT, 650, "Petrol - Indian Oil", "Transportation", ba_hdfc, PaymentMethod.DEBIT_CARD, "Indian Oil"),
            (28, ExpenseType.DEBIT, 1500, "Cult.fit membership", "Healthcare & Medical", ba_icici, PaymentMethod.UPI, "Cult.fit"),
            (29, ExpenseType.CREDIT, 125000, "Salary - TechVista Solutions", "Salary & Income", ba_icici, PaymentMethod.NET_BANKING, "TechVista Solutions"),
        ]

        for days_ago, exp_type, amount, desc, cat_name, bank_acc, pay_method, merchant in expenses_data:
            db.add(Expense(
                user_id=user_id,
                bank_account_id=bank_acc.id,
                category_id=cat_map.get(cat_name),
                transaction_date=now - timedelta(days=days_ago),
                transaction_type=exp_type,
                amount=float(amount),
                description=desc,
                merchant_name=merchant,
                payment_method=pay_method,
                is_categorized=True,
            ))

        print(f"  {len(expenses_data)} expenses created")

        # ══════════════════════════════════════════════════════════════════════════
        # 10. ALERTS
        # ══════════════════════════════════════════════════════════════════════════
        print("Creating alerts...")
        # Find specific assets for alert references
        reliance = next((a for a in all_assets if a.name == "Reliance Industries"), None)
        infosys = next((a for a in all_assets if a.name == "Infosys"), None)
        hdfc_fd = next((a for a in all_assets if a.name == "HDFC Bank FD 7.25%"), None)
        lic = next((a for a in all_assets if a.name == "LIC Jeevan Anand"), None)

        alerts_data = [
            (AlertType.PRICE_CHANGE, AlertSeverity.WARNING,
             "Infosys down 6.7% this week",
             "Infosys has declined from ₹1,500 to ₹1,400 (-6.67%). The IT sector is facing headwinds due to global macro uncertainty. Consider reviewing your position.",
             "Review your Infosys holdings and consider if this is a buying opportunity or time to cut losses.",
             infosys, False, 1),
            (AlertType.DIVIDEND_ANNOUNCEMENT, AlertSeverity.INFO,
             "TCS declares interim dividend of ₹10/share",
             "Tata Consultancy Services has announced an interim dividend of ₹10 per share. Record date: March 15, 2026. You hold 25 shares — expected payout: ₹250.",
             "No action needed. Dividend will be credited to your bank account.",
             None, True, 3),
            (AlertType.MATURITY_REMINDER, AlertSeverity.WARNING,
             "HDFC FD maturing in 12 months",
             "Your HDFC Bank Fixed Deposit of ₹5,00,000 at 7.25% is maturing on " + (today + timedelta(days=365)).strftime("%B %d, %Y") + ". Current FD rates are trending lower.",
             "Consider renewing the FD or exploring alternative investment options.",
             hdfc_fd, False, 5),
            (AlertType.REBALANCE_SUGGESTION, AlertSeverity.INFO,
             "Portfolio heavily weighted toward equities",
             "Your equity allocation (stocks + MFs) is ~45% of your portfolio. Consider rebalancing to maintain your target allocation.",
             "Review your asset allocation strategy. Consider increasing debt or gold allocation.",
             None, False, 7),
            (AlertType.PRICE_CHANGE, AlertSeverity.CRITICAL,
             "Reliance hits 52-week high!",
             "Reliance Industries has reached ₹2,900, a new 52-week high. Your holding is up 20.83% (₹25,000 profit). Consider booking partial profits.",
             "Consider selling 20-30% of your Reliance holding to book profits.",
             reliance, False, 2),
        ]

        for a_type, severity, title, message, action, asset_ref, is_read, days_ago in alerts_data:
            db.add(Alert(
                user_id=user_id,
                asset_id=asset_ref.id if asset_ref else None,
                alert_type=a_type,
                severity=severity,
                title=title,
                message=message,
                suggested_action=action,
                is_read=is_read,
                is_dismissed=False,
                is_actionable=True,
                alert_date=now - timedelta(days=days_ago),
            ))

        print(f"  {len(alerts_data)} alerts created")

        # ══════════════════════════════════════════════════════════════════════════
        # COMMIT ALL
        # ══════════════════════════════════════════════════════════════════════════
        db.commit()
        print("\n" + "=" * 60)
        print("Demo user seeded successfully!")
        print("=" * 60)
        print(f"  Email:         demouser@portact.com")
        print(f"  Password:      portact1")
        print(f"  Name:          Rahul Sharma")
        print(f"  Portfolios:    Default (id={portfolio_id}), Retirement (id={retirement_portfolio_id})")
        print(f"  Assets:        {len(all_assets)} (Default: {retirement_assets_start}, Retirement: {retirement_asset_count})")
        print(f"  Transactions:  {len(transactions)}")
        print(f"  MF Holdings:   {len(mf_holdings)}")
        print(f"  Snapshots:     30 days")
        print(f"  Expenses:      {len(expenses_data)}")
        print(f"  Alerts:        {len(alerts_data)}")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\nError seeding demo user: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("PortAct Demo User Seeder")
    print("=" * 60)
    seed_demo_user()
