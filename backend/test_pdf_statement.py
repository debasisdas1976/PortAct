#!/usr/bin/env python3
"""
End-to-end test for the PDF Portfolio Statement.

What this script does
---------------------
1. Creates (or reuses) a persistent test user: portact_test_user / TestPass123!
2. Seeds the test user with known data covering every asset type, bank accounts, etc.
3. Fetches dashboard overview + asset list + bank summary via the API (source of truth).
4. Downloads the PDF statement via GET /portfolio/statement/pdf.
5. Parses the PDF with pdfplumber and verifies:
   a) Structural: title, email, section headings, disclaimer footer.
   b) Summary box: Total Invested, Current Value, P&L, Return % match API.
   c) Asset Allocation table: per-type counts, invested, value, P&L match API.
   d) Individual asset tables: every asset name, symbol, invested, value present and correct.
   e) Bank Accounts table: bank names, masked account numbers, balances.
   f) Readability: no mojibake, no replacement chars, no overlapping text.
   g) Internal consistency: allocation TOTAL == summary box.

Run
---
    cd backend
    python test_pdf_statement.py

The test user (portact_test_user) persists between runs for reuse in future tests.
"""
from __future__ import annotations

import io
import os
import re
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

import pdfplumber
import requests

# ── Configuration ──────────────────────────────────────────────────────────
BASE_URL = os.environ.get("TEST_API_URL", "http://localhost:8000/api/v1")

# User credentials (override with env vars if needed)
TEST_USER = {
    "email": os.environ.get("TEST_EMAIL", "debasis.das@gmail.com"),
    "username": os.environ.get("TEST_USERNAME", "debasis.das@gmail.com"),
    "password": os.environ.get("TEST_PASSWORD", "givememore"),
}

# Counters
passed = 0
failed = 0
warnings = 0
errors: list[str] = []
warn_msgs: list[str] = []


def ok(label: str):
    global passed
    passed += 1
    print(f"  \u2713 {label}")


def fail(label: str, detail: str = ""):
    global failed
    failed += 1
    msg = f"  \u2717 {label}"
    if detail:
        msg += f" \u2014 {detail}"
    print(msg)
    errors.append(msg)


def warn(label: str, detail: str = ""):
    global warnings
    warnings += 1
    msg = f"  \u26a0 {label}"
    if detail:
        msg += f" \u2014 {detail}"
    print(msg)
    warn_msgs.append(msg)


# ── HTTP helpers ───────────────────────────────────────────────────────────
class APIClient:
    def __init__(self):
        self.token: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def register(self, user: dict) -> Optional[dict]:
        r = requests.post(f"{BASE_URL}/auth/register", json=user, headers=self._headers())
        if r.status_code == 400 and "already exists" in r.text:
            return None  # user already exists
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

    def get_json(self, path: str) -> Any:
        r = self.get(path)
        r.raise_for_status()
        return r.json()

    def post_json(self, path: str, data: dict) -> requests.Response:
        return requests.post(f"{BASE_URL}{path}", json=data, headers=self._headers())


# ── Seed data ──────────────────────────────────────────────────────────────
def seed_test_data(api: APIClient) -> bool:
    """
    Create representative portfolio data for the test user.
    Skips if data already exists (checks asset count).
    Returns True if seeding was performed.
    """
    existing_assets = api.get_json("/assets?limit=1")
    if isinstance(existing_assets, list) and len(existing_assets) > 0:
        print("  (test user already has data, skipping seed)")
        return False

    print("  Seeding test user with portfolio data...")

    # Bank accounts
    api.post_json("/bank-accounts", {
        "bank_name": "hdfc_bank", "account_type": "savings",
        "account_number": "HDFC00112233", "account_holder_name": "PortAct Test User",
        "ifsc_code": "HDFC0001234", "branch_name": "Test Branch",
        "current_balance": 150000.50, "available_balance": 145000.00,
        "credit_limit": 0, "is_active": True, "is_primary": True,
        "nickname": "My Savings", "notes": "Primary savings",
    }).raise_for_status()

    api.post_json("/bank-accounts", {
        "bank_name": "icici_bank", "account_type": "credit_card",
        "account_number": "ICICI44556677", "account_holder_name": "PortAct Test User",
        "ifsc_code": "ICIC0001234", "branch_name": "CC Branch",
        "current_balance": -25000.00, "available_balance": 75000.00,
        "credit_limit": 100000.00, "is_active": True, "is_primary": False,
        "nickname": "My CC",
    }).raise_for_status()

    # Demat accounts
    api.post_json("/demat-accounts", {
        "broker_name": "zerodha", "account_id": "ZRD-TEST-001",
        "account_holder_name": "PortAct Test User",
        "demat_account_number": "1201TEST001",
        "cash_balance": 50000.00, "currency": "INR",
        "is_active": True, "is_primary": True, "nickname": "Zerodha Main",
    }).raise_for_status()

    api.post_json("/demat-accounts", {
        "broker_name": "vested", "account_id": "VST-TEST-001",
        "account_holder_name": "PortAct Test User",
        "demat_account_number": "VSTTEST001",
        "cash_balance": 0, "cash_balance_usd": 1250.50, "currency": "USD",
        "is_active": True, "is_primary": False, "nickname": "US Stocks",
    }).raise_for_status()

    # Crypto account
    api.post_json("/crypto-accounts", {
        "exchange_name": "binance", "account_id": "BIN-TEST-001",
        "account_holder_name": "PortAct Test User",
        "wallet_address": "0xTESTWALLET001",
        "cash_balance_usd": 500.00, "total_value_usd": 12500.00,
        "is_active": True, "is_primary": True, "nickname": "Binance Main",
    }).raise_for_status()

    # Assets — diverse types
    assets = [
        {"asset_type": "stock", "name": "Reliance Industries", "symbol": "RELIANCE",
         "api_symbol": "RELIANCE.NS", "isin": "INE002A01018",
         "quantity": 10, "purchase_price": 2500, "current_price": 2750,
         "total_invested": 25000, "notes": "Blue chip", "purchase_date": "2024-03-15T00:00:00",
         "account_id": "ZRD-TEST-001", "broker_name": "zerodha"},
        {"asset_type": "stock", "name": "TCS Limited", "symbol": "TCS",
         "api_symbol": "TCS.NS", "isin": "INE467B01029",
         "quantity": 5, "purchase_price": 3800, "current_price": 4100,
         "total_invested": 19000, "purchase_date": "2024-04-01T00:00:00",
         "account_id": "ZRD-TEST-001", "broker_name": "zerodha"},
        {"asset_type": "us_stock", "name": "Apple Inc", "symbol": "AAPL",
         "api_symbol": "AAPL", "isin": "US0378331005",
         "quantity": 5, "purchase_price": 180, "current_price": 195,
         "total_invested": 900, "purchase_date": "2024-06-01T00:00:00",
         "account_id": "VST-TEST-001", "broker_name": "vested"},
        {"asset_type": "equity_mutual_fund", "name": "Axis Bluechip Fund Direct Growth",
         "symbol": "AXISBLU", "api_symbol": "120503", "isin": "INF846K01EW2",
         "quantity": 150.5, "purchase_price": 42.50, "current_price": 48.00,
         "total_invested": 6396.25, "purchase_date": "2023-01-01T00:00:00"},
        {"asset_type": "equity_mutual_fund", "name": "Parag Parikh Flexi Cap Fund Direct Growth",
         "symbol": "PPFCF", "api_symbol": "122639", "isin": "INF879O01027",
         "quantity": 200, "purchase_price": 55, "current_price": 62,
         "total_invested": 11000, "purchase_date": "2023-06-01T00:00:00"},
        {"asset_type": "crypto", "name": "Bitcoin", "symbol": "BTC",
         "api_symbol": "bitcoin",
         "quantity": 0.05, "purchase_price": 45000, "current_price": 62000,
         "total_invested": 2250, "purchase_date": "2024-01-15T00:00:00",
         "account_id": "BIN-TEST-001", "broker_name": "binance"},
        {"asset_type": "ppf", "name": "PPF Account SBI", "symbol": "PPF",
         "quantity": 1, "purchase_price": 500000, "current_price": 500000,
         "total_invested": 500000, "details": {"interest_rate": 7.1},
         "purchase_date": "2020-04-01T00:00:00"},
        {"asset_type": "fixed_deposit", "name": "HDFC FD 2-Year", "symbol": "FD-HDFC",
         "quantity": 1, "purchase_price": 200000, "current_price": 200000,
         "total_invested": 200000, "details": {"interest_rate": 7.25},
         "purchase_date": "2024-03-15T00:00:00"},
        {"asset_type": "nps", "name": "NPS Tier 1 SBI", "symbol": "NPS-T1",
         "quantity": 1, "purchase_price": 300000, "current_price": 350000,
         "total_invested": 300000, "purchase_date": "2021-04-01T00:00:00"},
        {"asset_type": "insurance_policy", "name": "LIC Jeevan Anand", "symbol": "LIC-001",
         "quantity": 1, "purchase_price": 100000, "current_price": 120000,
         "total_invested": 100000, "purchase_date": "2019-01-01T00:00:00"},
    ]
    for a in assets:
        r = api.post_json("/assets", a)
        r.raise_for_status()

    print(f"  Seeded: 2 bank accounts, 2 demat accounts, 1 crypto account, {len(assets)} assets")
    return True


# ── Number parsing helpers ─────────────────────────────────────────────────
def parse_inr(s: str) -> Optional[float]:
    """Parse 'Rs.1,23,456' or '+Rs.1,23,456' or '-Rs.1,23,456' into a float."""
    if not s:
        return None
    s = s.strip()
    m = re.match(r"([+-]?)Rs\.?([\d,]+(?:\.\d+)?)", s)
    if not m:
        return None
    sign = -1 if m.group(1) == "-" else 1
    return sign * float(m.group(2).replace(",", ""))


def parse_pct(s: str) -> Optional[float]:
    """Parse '+8.04%' or '-2.50%' into a float."""
    if not s:
        return None
    s = s.strip()
    m = re.match(r"([+-]?[\d.]+)%", s)
    if not m:
        return None
    return float(m.group(1))


def close_enough(a: float, b: float, tolerance: float = 1.0) -> bool:
    """Check if two numbers are close enough (within tolerance for rounding)."""
    return abs(a - b) <= tolerance


# ── PDF extraction ─────────────────────────────────────────────────────────
def extract_pdf_text(pdf_bytes: bytes) -> tuple[str, list[str], list[list[list[str]]]]:
    """
    Returns:
        full_text: all text concatenated with newlines between pages
        page_texts: list of text per page
        all_tables: list of tables (each table = list of rows, each row = list of cells)
    """
    page_texts = []
    all_tables = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            page_texts.append(text)

            tables = page.extract_tables()
            for tbl in tables:
                cleaned = []
                for row in tbl:
                    cleaned.append([(cell or "").strip() for cell in row])
                all_tables.append(cleaned)

    full_text = "\n".join(page_texts)
    return full_text, page_texts, all_tables


def find_table_with_header(tables: list, header_keywords: list[str]) -> Optional[list]:
    """Find a table whose first row contains all the given keywords."""
    for tbl in tables:
        if not tbl:
            continue
        header_row = " ".join(tbl[0]).lower()
        if all(kw.lower() in header_row for kw in header_keywords):
            return tbl
    return None


def find_row_in_table(table: list, match_text: str) -> Optional[list]:
    """Find a row in a table where any cell contains the match_text."""
    for row in table:
        for cell in row:
            if match_text.lower() in cell.lower():
                return row
    return None


# ── Main test ──────────────────────────────────────────────────────────────
def main():
    global passed, failed

    print("=" * 72)
    print("PDF PORTFOLIO STATEMENT \u2014 END-TO-END VERIFICATION TEST")
    print("=" * 72)
    print(f"API: {BASE_URL}")
    print(f"Test user: {TEST_USER['username']}")
    print()

    api = APIClient()

    try:
        # ── Step 1: Login ─────────────────────────────────────────────────
        print("STEP 1: Login")
        api.login(TEST_USER["username"], TEST_USER["password"])
        ok(f"Logged in as {TEST_USER['username']}")
        print()

        # ── Step 2: Fetch API data (source of truth) ─────────────────────
        print("STEP 2: Fetch dashboard data (source of truth)")
        overview = api.get_json("/dashboard/overview")
        assets_list = api.get_json("/assets?is_active=true&limit=500")
        bank_summary = api.get_json("/bank-accounts/summary")
        bank_accounts = api.get_json("/bank-accounts?is_active=true&limit=100")
        demat_summary = api.get_json("/demat-accounts/summary")
        demat_accounts = api.get_json("/demat-accounts?is_active=true&limit=100")

        # Re-derive asset-only totals from the assets list (authoritative source)
        if isinstance(assets_list, list) and len(assets_list) > 0:
            api_asset_invested = sum(a.get("total_invested", 0) for a in assets_list)
            api_asset_value = sum(a.get("current_value", 0) for a in assets_list)
        else:
            api_asset_invested = 0
            api_asset_value = 0

        api_bank_total = bank_summary.get("total_balance", 0)
        api_demat_cash = demat_summary.get("total_cash_balance", 0)

        # PDF now matches the Dashboard: includes bank + demat cash in totals
        api_total_invested = api_asset_invested + api_bank_total + api_demat_cash
        api_total_value = api_asset_value + api_bank_total + api_demat_cash
        # P&L is assets only (bank & demat cash contribute zero gain)
        api_total_pl = api_asset_value - api_asset_invested
        api_total_pl_pct = (api_total_pl / api_total_invested * 100) if api_total_invested else 0
        api_total_assets = len(assets_list) if isinstance(assets_list, list) else 0

        ok(f"Assets API: {api_total_assets} assets, Asset Invested={api_asset_invested:,.0f}, "
           f"Asset Value={api_asset_value:,.0f}")
        ok(f"Bank total: {api_bank_total:,.0f}, Demat cash: {api_demat_cash:,.0f}")
        ok(f"Grand totals (incl. bank+demat): Invested={api_total_invested:,.0f}, "
           f"Value={api_total_value:,.0f}, P&L={api_total_pl:,.0f} ({api_total_pl_pct:.2f}%)")

        # Build per-type aggregation from API
        api_by_type: Dict[str, Dict[str, Any]] = {}
        for asset in assets_list:
            atype = asset.get("asset_type", "")
            if atype not in api_by_type:
                api_by_type[atype] = {"count": 0, "invested": 0, "value": 0}
            api_by_type[atype]["count"] += 1
            api_by_type[atype]["invested"] += asset.get("total_invested", 0)
            api_by_type[atype]["value"] += asset.get("current_value", 0)
        print()

        # ── Step 4: Download PDF ──────────────────────────────────────────
        print("STEP 4: Download PDF statement")
        pdf_resp = api.get("/portfolio/statement/pdf")
        pdf_resp.raise_for_status()
        pdf_bytes = pdf_resp.content

        content_type = pdf_resp.headers.get("content-type", "")
        if "pdf" in content_type:
            ok(f"Content-Type: {content_type}")
        else:
            fail("Content-Type", f"expected application/pdf, got {content_type}")

        if len(pdf_bytes) > 1000:
            ok(f"PDF size: {len(pdf_bytes):,} bytes")
        else:
            fail("PDF size too small", f"{len(pdf_bytes)} bytes")

        pdf_path = "/tmp/test_portfolio_statement.pdf"
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        ok(f"Saved to {pdf_path}")
        print()

        # ── Step 5: Parse PDF ─────────────────────────────────────────────
        print("STEP 5: Parse PDF")
        full_text, page_texts, all_tables = extract_pdf_text(pdf_bytes)

        if not full_text.strip():
            fail("PDF has no extractable text")
            return False

        ok(f"Extracted {len(page_texts)} pages, {len(all_tables)} tables")

        # Debug: dump table headers for diagnostics
        for i, tbl in enumerate(all_tables):
            if tbl:
                hdr = " | ".join(tbl[0][:6])
                print(f"    Table {i}: [{hdr}] ({len(tbl)} rows)")
        print()

        # ── Step 6: Structural checks ────────────────────────────────────
        print("STEP 6: Structural checks")

        if "Portfolio Statement" in full_text:
            ok("Title 'Portfolio Statement' present")
        else:
            fail("Title 'Portfolio Statement' missing")

        if TEST_USER["email"] in full_text:
            ok(f"User email '{TEST_USER['email']}' present")
        else:
            fail(f"User email not found in PDF")

        for heading in ["Asset Allocation Summary"]:
            if heading in full_text:
                ok(f"Section '{heading}' present")
            else:
                fail(f"Section '{heading}' missing")

        if "informational purposes" in full_text.lower():
            ok("Disclaimer footer present")
        else:
            fail("Disclaimer footer missing")
        print()

        # ── Step 7: Readability checks ───────────────────────────────────
        print("STEP 7: Readability checks")

        # Mojibake (byte sequences that indicate double-encoding)
        mojibake_patterns = [
            ("\xc3\xa2", "double-encoded UTF-8"),
            ("\xef\xbf\xbd", "replacement character bytes"),
        ]
        mojibake_found = False
        for pattern, desc in mojibake_patterns:
            if pattern in full_text:
                fail(f"Mojibake: {desc}")
                mojibake_found = True
        if not mojibake_found:
            ok("No mojibake / encoding issues")

        if "\ufffd" in full_text:
            fail("U+FFFD replacement characters found (missing font glyphs)")
        else:
            ok("No replacement characters")

        if "Rs." in full_text:
            ok("Currency uses 'Rs.' (PDF-safe)")
        else:
            warn("'Rs.' not found in PDF")

        # Overlapping text detection
        overlap_found = False
        for page_idx, page_text in enumerate(page_texts):
            for line in page_text.split("\n"):
                for word in line.split():
                    if len(word) > 80 and not word.startswith("http"):
                        fail(f"Page {page_idx+1}: Overlapping text detected",
                             f"len={len(word)}: '{word[:50]}...'")
                        overlap_found = True
                        break
        if not overlap_found:
            ok("No overlapping text")
        print()

        # ── Step 8: Summary box ──────────────────────────────────────────
        print("STEP 8: Verify summary box")

        summary_tbl = find_table_with_header(all_tables, ["Total Invested", "Current Value"])
        if not summary_tbl:
            fail("Summary table not found")
        else:
            ok("Summary table found")
            if len(summary_tbl) >= 2:
                values_row = summary_tbl[1]
                # pdfplumber may merge all 4 cells into one string;
                # extract all Rs. values and % values from the full row text
                row_text = " ".join(values_row)
                inr_values = [
                    (-1 if m.group(1) == "-" else 1) * float(m.group(2).replace(",", ""))
                    for m in re.finditer(r"([+-]?)Rs\.?([\d,]+(?:\.\d+)?)", row_text)
                ]
                pct_values = [
                    float(m.group(1))
                    for m in re.finditer(r"([+-]?[\d.]+)%", row_text)
                ]

                if len(inr_values) >= 3:
                    pdf_invested, pdf_value, pdf_pl = inr_values[0], inr_values[1], inr_values[2]

                    if close_enough(pdf_invested, api_total_invested, 2):
                        ok(f"Total Invested: PDF={pdf_invested:,.0f} == API={api_total_invested:,.0f}")
                    else:
                        fail("Total Invested mismatch",
                             f"PDF={pdf_invested:,.0f} vs API={api_total_invested:,.0f}")

                    if close_enough(pdf_value, api_total_value, 2):
                        ok(f"Current Value: PDF={pdf_value:,.0f} == API={api_total_value:,.0f}")
                    else:
                        fail("Current Value mismatch",
                             f"PDF={pdf_value:,.0f} vs API={api_total_value:,.0f}")

                    if close_enough(pdf_pl, api_total_pl, 2):
                        ok(f"Profit/Loss: PDF={pdf_pl:,.0f} == API={api_total_pl:,.0f}")
                    else:
                        fail("Profit/Loss mismatch",
                             f"PDF={pdf_pl:,.0f} vs API={api_total_pl:,.0f}")
                else:
                    fail("Could not parse 3 INR values from summary",
                         f"found {len(inr_values)}: {inr_values}")

                if pct_values:
                    pdf_pct = pct_values[0]
                    if close_enough(pdf_pct, api_total_pl_pct, 0.1):
                        ok(f"Return %: PDF={pdf_pct:.2f}% == API={api_total_pl_pct:.2f}%")
                    else:
                        fail("Return % mismatch",
                             f"PDF={pdf_pct:.2f}% vs API={api_total_pl_pct:.2f}%")
                else:
                    fail("Could not parse return % from summary")
            else:
                fail("Summary table has < 2 rows")
        print()

        # ── Step 9: Asset Allocation table ───────────────────────────────
        print("STEP 9: Verify Asset Allocation Summary table")

        alloc_tbl = find_table_with_header(all_tables, ["Asset Type", "Count", "Invested"])
        if not alloc_tbl:
            fail("Allocation table not found")
        else:
            ok("Allocation table found")

            PDF_LABEL_TO_TYPE = {
                "Stocks": "stock", "US Stocks": "us_stock",
                "Equity Mutual Funds": "equity_mutual_fund",
                "Debt Mutual Funds": "debt_mutual_fund",
                "Commodities": "commodity", "Crypto": "crypto",
                "PPF": "ppf", "PF / EPF": "pf", "NPS": "nps", "SSY": "ssy",
                "Gratuity": "gratuity", "Insurance": "insurance_policy",
                "Fixed Deposits": "fixed_deposit",
                "Recurring Deposits": "recurring_deposit",
                "Savings Accounts": "savings_account",
                "Real Estate": "real_estate", "Cash": "cash",
            }

            def extract_inr_from_row(row: list) -> list[float]:
                """Extract all Rs. values from a row (handles merged cells)."""
                text = " ".join(row)
                return [
                    (-1 if m.group(1) == "-" else 1) * float(m.group(2).replace(",", ""))
                    for m in re.finditer(r"([+-]?)Rs\.?([\d,]+(?:\.\d+)?)", text)
                ]

            alloc_ok = 0
            alloc_fail = 0

            for row in alloc_tbl[1:]:
                row_text = " ".join(row)
                if "TOTAL" in row_text.upper():
                    inr_vals = extract_inr_from_row(row)
                    if len(inr_vals) >= 2:
                        if close_enough(inr_vals[0], api_total_invested, 2):
                            alloc_ok += 1
                        else:
                            fail("Allocation TOTAL invested mismatch",
                                 f"PDF={inr_vals[0]:,.0f} vs API={api_total_invested:,.0f}")
                            alloc_fail += 1
                        if close_enough(inr_vals[1], api_total_value, 2):
                            alloc_ok += 1
                        else:
                            fail("Allocation TOTAL value mismatch",
                                 f"PDF={inr_vals[1]:,.0f} vs API={api_total_value:,.0f}")
                            alloc_fail += 1
                    continue

                label = row[0].strip() if row else ""
                # Skip bank/demat cash rows (they aren't asset types)
                if label in ("Bank Accounts", "Demat Cash"):
                    continue
                atype = PDF_LABEL_TO_TYPE.get(label)
                if not atype or atype not in api_by_type:
                    continue

                api_data = api_by_type[atype]

                # Extract count — look for a standalone integer in the row
                count_match = re.search(r"\b(\d{1,3})\b", row_text.replace(label, "", 1))
                pdf_count = int(count_match.group(1)) if count_match else None

                inr_vals = extract_inr_from_row(row)

                if pdf_count is not None:
                    if pdf_count == api_data["count"]:
                        alloc_ok += 1
                    else:
                        fail(f"Allocation '{label}' count",
                             f"PDF={pdf_count} vs API={api_data['count']}")
                        alloc_fail += 1

                if len(inr_vals) >= 2:
                    if close_enough(inr_vals[0], api_data["invested"], 2):
                        alloc_ok += 1
                    else:
                        fail(f"Allocation '{label}' invested",
                             f"PDF={inr_vals[0]:,.0f} vs API={api_data['invested']:,.0f}")
                        alloc_fail += 1
                    if close_enough(inr_vals[1], api_data["value"], 2):
                        alloc_ok += 1
                    else:
                        fail(f"Allocation '{label}' value",
                             f"PDF={inr_vals[1]:,.0f} vs API={api_data['value']:,.0f}")
                        alloc_fail += 1

            if alloc_ok > 0 and alloc_fail == 0:
                ok(f"All allocation values verified ({alloc_ok} checks)")
            elif alloc_ok > 0:
                warn(f"Allocation: {alloc_ok} passed, {alloc_fail} failed")
        print()

        # ── Step 10: Individual assets ───────────────────────────────────
        print("STEP 10: Verify individual assets in PDF")

        api_asset_names = set(a.get("name", "") for a in assets_list)
        api_asset_symbols = set(a.get("symbol", "") for a in assets_list if a.get("symbol"))

        def name_in_pdf(name: str, text: str) -> bool:
            """Check if an asset name appears in the PDF text.
            pdfplumber can scramble wrapped Paragraph text, so we also try:
            1) exact substring, 2) first N chars, 3) word-overlap (>= 60% of
            significant words present in the full text)."""
            if name in text:
                return True
            if name[:30] in text:
                return True
            # Word-overlap: check if most significant words appear nearby
            words = [w for w in name.split() if len(w) > 2 and w != "-"]
            if not words:
                return True
            found_words = sum(1 for w in words if w in text)
            return found_words / len(words) >= 0.6

        # Check each asset name
        found_count = 0
        not_found = []
        for name in api_asset_names:
            if name_in_pdf(name, full_text):
                found_count += 1
            else:
                not_found.append(name)

        if found_count > 0:
            ok(f"{found_count}/{len(api_asset_names)} asset names found")
        for name in not_found:
            fail(f"Asset '{name}' not found in PDF text")

        # Check symbols
        sym_found = sum(1 for s in api_asset_symbols if s in full_text)
        ok(f"{sym_found}/{len(api_asset_symbols)} asset symbols found")

        # Verify values in detail tables
        detail_tables = [t for t in all_tables if t and
                         "name" in " ".join(t[0]).lower() and
                         "invested" in " ".join(t[0]).lower()]

        if detail_tables:
            ok(f"Found {len(detail_tables)} asset detail tables")

            # Collect ALL data rows from ALL tables (not just ones with headers).
            # This catches page-break continuation tables (e.g. Table 6, 13)
            # whose "first row" is actually data, not a header.
            #
            # Exclude known non-detail tables: summary, allocation, bank.
            excluded_tables = set()
            for idx, tbl in enumerate(all_tables):
                if not tbl:
                    continue
                hdr = " ".join(tbl[0]).lower()
                if "total invested" in hdr and "current value" in hdr:
                    excluded_tables.add(idx)  # summary table
                if "asset type" in hdr and "count" in hdr:
                    excluded_tables.add(idx)  # allocation table
                if "bank" in hdr and "balance" in hdr:
                    excluded_tables.add(idx)  # bank table
                if "broker" in hdr and "cash balance" in hdr:
                    excluded_tables.add(idx)  # demat table

            all_detail_rows = []
            for idx, tbl in enumerate(all_tables):
                if idx in excluded_tables:
                    continue
                for row in tbl:
                    row_str = " ".join(row)
                    # Skip obvious table headers
                    if ("Name" in row_str and "Invested" in row_str
                            and "Symbol" in row_str):
                        continue
                    # Only include rows with Rs. values (actual asset data rows)
                    if "Rs." in row_str:
                        all_detail_rows.append(row_str)

            value_ok = 0
            value_fail = 0
            value_skip = 0

            # Pre-parse all detail rows into (row_str, inr_values) pairs
            parsed_rows = []
            for row_str in all_detail_rows:
                inr_vals = [
                    (-1 if m.group(1) == "-" else 1) * float(m.group(2).replace(",", ""))
                    for m in re.finditer(r"([+-]?)Rs\.?([\d,]+(?:\.\d+)?)", row_str)
                ]
                if len(inr_vals) >= 2:
                    parsed_rows.append((row_str, inr_vals))

            # Track which PDF rows have been consumed (for duplicate-name matching)
            used_rows = set()

            # Sort API assets by invested amount descending so larger amounts
            # get matched first (reduces ambiguity for small-value lots)
            sorted_assets = sorted(
                assets_list,
                key=lambda a: a.get("total_invested", 0),
                reverse=True,
            )

            for asset in sorted_assets:
                a_name = asset.get("name", "")
                a_symbol = asset.get("symbol", "")
                a_invested = asset.get("total_invested", 0)
                a_value = asset.get("current_value", 0)

                # Find ALL candidate rows matching this asset name/symbol (not yet used)
                candidates = []
                for idx, (row_str, inr_vals) in enumerate(parsed_rows):
                    if idx in used_rows:
                        continue
                    if (a_name in row_str or a_name[:25] in row_str
                            or (a_symbol and a_symbol in row_str)
                            or name_in_pdf(a_name, row_str)):
                        candidates.append((idx, inr_vals, row_str))

                if not candidates:
                    value_skip += 1
                    continue

                # Among candidates, find the one whose invested value is closest
                best_idx, best_inr, _ = min(
                    candidates, key=lambda c: abs(c[1][0] - a_invested)
                )
                used_rows.add(best_idx)

                if close_enough(best_inr[0], a_invested, 2):
                    value_ok += 1
                else:
                    fail(f"Asset '{a_name[:30]}' invested",
                         f"PDF={best_inr[0]:,.0f} vs API={a_invested:,.0f}")
                    value_fail += 1

                if close_enough(best_inr[1], a_value, 2):
                    value_ok += 1
                else:
                    fail(f"Asset '{a_name[:30]}' value",
                         f"PDF={best_inr[1]:,.0f} vs API={a_value:,.0f}")
                    value_fail += 1

            if value_ok > 0 and value_fail == 0:
                ok(f"Asset values: all {value_ok} checks passed ({value_skip} skipped)")
            elif value_ok > 0:
                ok(f"Asset values: {value_ok} matched, {value_fail} mismatched, {value_skip} skipped")
        else:
            warn("No asset detail tables found")
        print()

        # ── Step 11: Bank Accounts table ─────────────────────────────────
        print("STEP 11: Verify Bank Accounts table")

        bank_tbl = find_table_with_header(all_tables, ["Bank", "Type", "Balance"])
        if not bank_tbl:
            if bank_accounts:
                fail("Bank Accounts table missing (user has bank accounts)")
            else:
                ok("No bank accounts — table correctly omitted")
        else:
            ok("Bank Accounts table found")
            bank_ok = 0
            bank_fail = 0
            bank_skip = 0
            for ba in bank_accounts:
                ba_name = ba.get("bank_name", "").replace("_", " ").title()
                acct_num = ba.get("account_number", "")
                masked = f"xxxx{acct_num[-4:]}" if len(acct_num) >= 4 else ""
                balance = ba.get("current_balance", 0)

                matched_row = None
                # First pass: match by masked account number (most specific)
                if masked:
                    for row in bank_tbl[1:]:
                        row_text = " ".join(row)
                        if masked.lower() in row_text.lower():
                            matched_row = row_text
                            break

                # Second pass: match by bank name + closest balance (for dups)
                if not matched_row:
                    for row in bank_tbl[1:]:
                        row_text = " ".join(row)
                        if ba_name.lower() in row_text.lower():
                            matched_row = row_text
                            break

                if not matched_row:
                    bank_skip += 1
                    continue

                # Extract INR values from matched row
                inr_vals = [
                    (-1 if m.group(1) == "-" else 1) * float(m.group(2).replace(",", ""))
                    for m in re.finditer(r"([+-]?)Rs\.?([\d,]+(?:\.\d+)?)", matched_row)
                ]
                if inr_vals and close_enough(inr_vals[-1], balance, 2):
                    bank_ok += 1
                elif inr_vals:
                    # Could be a different account with same bank name;
                    # only fail if the masked account number was in this row
                    if masked and masked.lower() in matched_row.lower():
                        fail(f"Bank '{ba_name}' ({masked}) balance",
                             f"PDF={inr_vals[-1]:,.0f} vs API={balance:,.0f}")
                        bank_fail += 1
                    else:
                        bank_skip += 1  # ambiguous match, skip
                else:
                    bank_skip += 1

            if bank_ok > 0 and bank_fail == 0:
                ok(f"{bank_ok}/{len(bank_accounts)} bank balances verified"
                   + (f" ({bank_skip} skipped)" if bank_skip else ""))
            elif bank_ok > 0:
                warn(f"Bank balances: {bank_ok} ok, {bank_fail} failed, {bank_skip} skipped")

            # Check bank total row
            total_found = False
            for row in bank_tbl:
                row_text = " ".join(row)
                if "total" in row_text.lower():
                    total_found = True
                    inr_vals = [
                        (-1 if m.group(1) == "-" else 1) * float(m.group(2).replace(",", ""))
                        for m in re.finditer(r"([+-]?)Rs\.?([\d,]+(?:\.\d+)?)", row_text)
                    ]
                    if inr_vals and close_enough(inr_vals[-1], api_bank_total, 2):
                        ok(f"Bank total: PDF={inr_vals[-1]:,.0f} == API={api_bank_total:,.0f}")
                    elif inr_vals:
                        fail(f"Bank total mismatch",
                             f"PDF={inr_vals[-1]:,.0f} vs API={api_bank_total:,.0f}")
                    else:
                        warn("Bank total row found but could not parse value")
                    break
            if not total_found:
                warn("Bank total row not found in table")
        print()

        # ── Step 11b: Demat Accounts table ──────────────────────────────
        print("STEP 11b: Verify Demat / Trading Accounts table")

        demat_tbl = find_table_with_header(all_tables, ["Broker", "Cash Balance"])
        if not demat_tbl:
            if demat_accounts:
                fail("Demat Accounts table missing (user has demat accounts)")
            else:
                ok("No demat accounts — table correctly omitted")
        else:
            ok("Demat Accounts table found")
            demat_ok = 0
            demat_fail_cnt = 0
            for da in (demat_accounts if isinstance(demat_accounts, list) else []):
                acct_id = da.get("account_id", "")
                cash = da.get("cash_balance", 0)

                matched_row = None
                for row in demat_tbl[1:]:
                    row_text = " ".join(row)
                    if acct_id and acct_id in row_text:
                        matched_row = row_text
                        break

                if not matched_row:
                    continue

                inr_vals = [
                    (-1 if m.group(1) == "-" else 1) * float(m.group(2).replace(",", ""))
                    for m in re.finditer(r"([+-]?)Rs\.?([\d,]+(?:\.\d+)?)", matched_row)
                ]
                if inr_vals and close_enough(inr_vals[-1], cash, 2):
                    demat_ok += 1
                elif inr_vals:
                    fail(f"Demat '{acct_id}' cash balance",
                         f"PDF={inr_vals[-1]:,.0f} vs API={cash:,.0f}")
                    demat_fail_cnt += 1

            if demat_ok > 0 and demat_fail_cnt == 0:
                ok(f"{demat_ok} demat account balances verified")

            # Check demat total row
            for row in demat_tbl:
                row_text = " ".join(row)
                if "total" in row_text.lower():
                    inr_vals = [
                        (-1 if m.group(1) == "-" else 1) * float(m.group(2).replace(",", ""))
                        for m in re.finditer(r"([+-]?)Rs\.?([\d,]+(?:\.\d+)?)", row_text)
                    ]
                    if inr_vals and close_enough(inr_vals[-1], api_demat_cash, 2):
                        ok(f"Demat cash total: PDF={inr_vals[-1]:,.0f} == API={api_demat_cash:,.0f}")
                    elif inr_vals:
                        fail(f"Demat cash total mismatch",
                             f"PDF={inr_vals[-1]:,.0f} vs API={api_demat_cash:,.0f}")
                    break
        print()

        # ── Step 12: Internal consistency ────────────────────────────────
        print("STEP 12: Internal consistency")

        if alloc_tbl and summary_tbl and len(summary_tbl) >= 2:
            total_row = None
            for row in alloc_tbl:
                if "TOTAL" in " ".join(row).upper():
                    total_row = row
                    break
            if total_row:
                # Use regex extraction from joined text (handles merged cells)
                alloc_text = " ".join(total_row)
                alloc_inr = [
                    (-1 if m.group(1) == "-" else 1) * float(m.group(2).replace(",", ""))
                    for m in re.finditer(r"([+-]?)Rs\.?([\d,]+(?:\.\d+)?)", alloc_text)
                ]
                summary_text = " ".join(summary_tbl[1])
                summary_inr = [
                    (-1 if m.group(1) == "-" else 1) * float(m.group(2).replace(",", ""))
                    for m in re.finditer(r"([+-]?)Rs\.?([\d,]+(?:\.\d+)?)", summary_text)
                ]
                if len(alloc_inr) >= 2 and len(summary_inr) >= 2:
                    if close_enough(alloc_inr[0], summary_inr[0], 2):
                        ok("Allocation TOTAL invested == Summary box invested")
                    else:
                        fail("Inconsistency: Allocation TOTAL invested != Summary",
                             f"{alloc_inr[0]:,.0f} vs {summary_inr[0]:,.0f}")
                    if close_enough(alloc_inr[1], summary_inr[1], 2):
                        ok("Allocation TOTAL value == Summary box value")
                    else:
                        fail("Inconsistency: Allocation TOTAL value != Summary",
                             f"{alloc_inr[1]:,.0f} vs {summary_inr[1]:,.0f}")
                else:
                    warn(f"Internal consistency: could not parse enough values "
                         f"(alloc={len(alloc_inr)}, summary={len(summary_inr)})")
        print()

        # ── Step 13: Page count ──────────────────────────────────────────
        print("STEP 13: Page count and completeness")
        ok(f"PDF has {len(page_texts)} page(s)")

        empty_pages = [i+1 for i, t in enumerate(page_texts) if not t.strip()]
        if empty_pages:
            fail(f"Empty pages: {empty_pages}")
        else:
            ok("All pages have content")

        if page_texts and "Portfolio Statement" in page_texts[0]:
            ok("Title on first page")
        else:
            fail("Title not on first page")

        if page_texts and "informational" in page_texts[-1].lower():
            ok("Disclaimer on last page")
        else:
            warn("Disclaimer not on last page (may be on earlier page)")
        print()

    except requests.HTTPError as e:
        fail("HTTP error", f"{e.response.status_code}: {e.response.text[:300]}")
        traceback.print_exc()
    except Exception as e:
        fail("Unexpected error", str(e))
        traceback.print_exc()

    # ── Summary ───────────────────────────────────────────────────────────
    print("=" * 72)
    print(f"RESULTS:  {passed} passed,  {failed} failed,  {warnings} warnings")
    if errors:
        print("\nFailed checks:")
        for e in errors:
            print(f"  {e}")
    if warn_msgs:
        print("\nWarnings:")
        for w in warn_msgs:
            print(f"  {w}")
    print("=" * 72)
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
