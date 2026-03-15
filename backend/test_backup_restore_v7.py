#!/usr/bin/env python3
"""
Comprehensive Backup & Restore v7.0 Test

1. Login as demouser, export portfolio
2. Verify export contains all v7.0 sections
3. Register a temp user, restore the backup into it
4. Export from temp user, compare with original
5. Verify idempotency (second restore skips all)
6. Cleanup temp user
"""
from __future__ import annotations
import json, sys, os, uuid, io, traceback
from datetime import datetime
from typing import Any, Dict, Optional
import requests

BASE_URL = os.environ.get("TEST_API_URL", "http://localhost:8000/api/v1")
UNIQUE = uuid.uuid4().hex[:8]

DEMO_USER = {"username": "demouser@portact.com", "password": "portact1"}
TEMP_USER = {
    "email": f"test_restore_{UNIQUE}@test.com",
    "username": f"test_restore_{UNIQUE}",
    "password": "TestPass123!",
    "full_name": "Temp Restore User",
}

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


class APIClient:
    def __init__(self):
        self.token: Optional[str] = None

    def _headers(self) -> Dict[str, str]:
        h = {"Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def login(self, username: str, password: str) -> str:
        r = requests.post(
            f"{BASE_URL}/auth/login",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        r.raise_for_status()
        self.token = r.json()["access_token"]
        return self.token

    def register(self, user: dict) -> dict:
        r = requests.post(f"{BASE_URL}/auth/register", json=user, headers=self._headers())
        r.raise_for_status()
        return r.json()

    def get(self, path: str, **kw) -> requests.Response:
        return requests.get(f"{BASE_URL}{path}", headers=self._headers(), **kw)

    def post(self, path: str, **kw) -> requests.Response:
        return requests.post(f"{BASE_URL}{path}", headers=self._headers(), **kw)

    def delete(self, path: str) -> requests.Response:
        return requests.delete(f"{BASE_URL}{path}", headers=self._headers())


def verify_export_structure(payload: dict):
    """Verify v7.0 export has all expected top-level keys."""
    print("\n── Verify Export Structure ──")

    version = payload.get("export_version")
    if version == "7.0":
        ok(f"Export version: {version}")
    else:
        fail("Export version", f"expected 7.0, got {version}")

    expected_keys = {
        "export_version", "exported_at", "exported_by",
        "user_profile",
        "portfolios", "bank_accounts", "demat_accounts",
        "crypto_accounts", "assets", "expense_categories",
        "expenses", "transactions", "mutual_fund_holdings",
        "alerts", "portfolio_snapshots",
        "asset_attributes", "asset_attribute_values",
        "asset_attribute_assignments",
        "mf_systematic_plans",
        "app_settings", "master_data",
        "macro_data_points", "reference_rates", "nse_holidays",
    }
    actual_keys = set(payload.keys())
    missing = expected_keys - actual_keys
    extra = actual_keys - expected_keys
    if not missing:
        ok(f"All {len(expected_keys)} expected top-level keys present")
    else:
        fail("Missing keys", str(missing))
    if extra:
        fail("Unexpected extra keys", str(extra))


def verify_export_counts(payload: dict):
    """Print counts for every section."""
    print("\n── Export Data Counts ──")

    # User-scoped sections
    user_sections = [
        "portfolios", "bank_accounts", "demat_accounts", "crypto_accounts",
        "assets", "expense_categories", "expenses", "transactions",
        "mutual_fund_holdings", "alerts", "portfolio_snapshots",
        "asset_attributes", "asset_attribute_values", "asset_attribute_assignments",
        "mf_systematic_plans",
    ]
    for section in user_sections:
        data = payload.get(section, [])
        count = len(data) if isinstance(data, list) else 0
        if count > 0:
            ok(f"{section}: {count} records")
        else:
            print(f"  · {section}: 0 records (empty)")

    # Nested asset snapshots
    total_asset_snaps = sum(
        len(ps.get("asset_snapshots", []))
        for ps in payload.get("portfolio_snapshots", [])
    )
    if total_asset_snaps > 0:
        ok(f"asset_snapshots (nested): {total_asset_snaps} records")
    else:
        print(f"  · asset_snapshots: 0")

    # User profile
    profile = payload.get("user_profile", {})
    if profile and isinstance(profile, dict):
        non_null = sum(1 for v in profile.values() if v is not None)
        ok(f"user_profile: {non_null}/{len(profile)} fields populated")
    else:
        fail("user_profile", "missing or empty")

    # System sections
    print("\n── System/Config Data Counts ──")

    settings = payload.get("app_settings", [])
    if len(settings) > 0:
        secret_count = sum(1 for s in settings if s.get("value_type") == "secret")
        secret_empty = sum(1 for s in settings if s.get("value_type") == "secret" and not s.get("value"))
        ok(f"app_settings: {len(settings)} settings ({secret_count} secrets, {secret_empty} masked)")
    else:
        fail("app_settings", "empty")

    master = payload.get("master_data", {})
    master_sections = ["asset_categories", "asset_types", "banks", "brokers",
                       "crypto_exchanges", "institutions"]
    for ms in master_sections:
        data = master.get(ms, [])
        if len(data) > 0:
            ok(f"master_data.{ms}: {len(data)} records")
        else:
            fail(f"master_data.{ms}", "empty")

    for section in ["macro_data_points", "reference_rates", "nse_holidays"]:
        data = payload.get(section, [])
        if len(data) > 0:
            ok(f"{section}: {len(data)} records")
        else:
            print(f"  · {section}: 0 records")


def compare_exports(source: dict, target: dict):
    """Compare source and target exports by counts and key values."""
    print("\n── Compare Source vs Target Export ──")

    # Compare user-scoped list sections by count
    list_sections = [
        "portfolios", "bank_accounts", "demat_accounts", "crypto_accounts",
        "assets", "expense_categories", "expenses", "transactions",
        "mutual_fund_holdings", "alerts", "portfolio_snapshots",
        "asset_attributes", "asset_attribute_values", "asset_attribute_assignments",
        "mf_systematic_plans",
    ]
    for section in list_sections:
        src = source.get(section, [])
        tgt = target.get(section, [])
        src_count = len(src) if isinstance(src, list) else 0
        tgt_count = len(tgt) if isinstance(tgt, list) else 0

        # Expense categories: source may include system categories, target may differ
        if section == "expense_categories":
            # Compare only user-defined categories
            src_user = [c for c in src if not c.get("is_system")]
            tgt_user = [c for c in tgt if not c.get("is_system")]
            if len(src_user) == len(tgt_user):
                ok(f"{section}: user-defined counts match ({len(src_user)})")
            else:
                fail(f"{section} user-defined count", f"source={len(src_user)}, target={len(tgt_user)}")
            continue

        # Portfolios: target gets "Default" auto-created, source has its own
        if section == "portfolios":
            src_names = sorted(p.get("name", "") for p in src)
            tgt_names = sorted(p.get("name", "") for p in tgt)
            if src_names == tgt_names:
                ok(f"{section}: names match ({src_count})")
            else:
                # At minimum, all source portfolios should exist in target
                missing = set(src_names) - set(tgt_names)
                if missing:
                    fail(f"{section} names", f"missing in target: {missing}")
                else:
                    ok(f"{section}: all source portfolios present in target ({tgt_count} total)")
            continue

        if src_count == tgt_count:
            ok(f"{section}: counts match ({src_count})")
        else:
            fail(f"{section} count mismatch", f"source={src_count}, target={tgt_count}")

    # Compare assets by name and key fields
    print("\n── Asset-level Comparison ──")
    src_assets = {a["name"]: a for a in source.get("assets", [])}
    tgt_assets = {a["name"]: a for a in target.get("assets", [])}

    missing_in_target = set(src_assets.keys()) - set(tgt_assets.keys())
    if missing_in_target:
        fail("Assets missing in target", str(missing_in_target))
    else:
        ok(f"All {len(src_assets)} assets present in target")

    # Compare key financial fields
    value_mismatches = 0
    for name, src_a in src_assets.items():
        tgt_a = tgt_assets.get(name)
        if not tgt_a:
            continue
        for field in ["asset_type", "quantity", "total_invested", "current_value", "symbol"]:
            sv = src_a.get(field)
            tv = tgt_a.get(field)
            if sv is None and tv is None:
                continue
            if isinstance(sv, (int, float)) and isinstance(tv, (int, float)):
                if abs(sv - tv) > 0.01:
                    fail(f"Asset '{name}'.{field}", f"source={sv}, target={tv}")
                    value_mismatches += 1
            elif str(sv) != str(tv):
                fail(f"Asset '{name}'.{field}", f"source={sv!r}, target={tv!r}")
                value_mismatches += 1
    if value_mismatches == 0:
        ok("All asset financial fields match")

    # Compare snapshot counts
    src_snaps = sum(len(ps.get("asset_snapshots", [])) for ps in source.get("portfolio_snapshots", []))
    tgt_snaps = sum(len(ps.get("asset_snapshots", [])) for ps in target.get("portfolio_snapshots", []))
    if src_snaps == tgt_snaps:
        ok(f"Asset snapshot counts match ({src_snaps})")
    else:
        fail("Asset snapshot count", f"source={src_snaps}, target={tgt_snaps}")

    # Compare system data (these should be identical since they're global)
    print("\n── System Data Comparison ──")
    for section in ["app_settings", "macro_data_points", "reference_rates", "nse_holidays"]:
        src_data = source.get(section, [])
        tgt_data = target.get(section, [])
        if len(src_data) == len(tgt_data):
            ok(f"{section}: counts match ({len(src_data)})")
        else:
            fail(f"{section} count", f"source={len(src_data)}, target={len(tgt_data)}")

    src_master = source.get("master_data", {})
    tgt_master = target.get("master_data", {})
    for ms in ["asset_categories", "asset_types", "banks", "brokers", "crypto_exchanges", "institutions"]:
        if len(src_master.get(ms, [])) == len(tgt_master.get(ms, [])):
            ok(f"master_data.{ms}: counts match ({len(src_master.get(ms, []))})")
        else:
            fail(f"master_data.{ms}", f"source={len(src_master.get(ms, []))}, target={len(tgt_master.get(ms, []))}")


def verify_idempotency(stats: dict):
    """Verify second restore imported 0 user-scoped records."""
    print("\n── Idempotency Check ──")
    user_sections = [
        "portfolios", "bank_accounts", "demat_accounts", "crypto_accounts",
        "assets", "expense_categories", "expenses", "transactions",
        "mutual_fund_holdings", "alerts", "portfolio_snapshots", "asset_snapshots",
        "asset_attributes", "asset_attribute_values", "asset_attribute_assignments",
        "mf_systematic_plans",
    ]
    all_ok = True
    for section in user_sections:
        s = stats.get(section, {})
        imported = s.get("imported", 0)
        skipped = s.get("skipped", 0)
        if imported > 0:
            fail(f"Idempotency {section}", f"{imported} imported (expected 0)")
            all_ok = False
        else:
            ok(f"{section}: 0 imported, {skipped} skipped")
    if all_ok:
        ok("Idempotency PASSED — no duplicates on second restore")


def cleanup_temp_user():
    """Remove temp user from DB."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.core.config import settings
        from app.models.user import User

        engine = create_engine(settings.DATABASE_URL)
        Session = sessionmaker(bind=engine)
        db = Session()
        u = db.query(User).filter(User.username == TEMP_USER["username"]).first()
        if u:
            db.delete(u)
            db.commit()
            print(f"  Cleaned up temp user: {TEMP_USER['username']}")
        else:
            print(f"  Temp user not found (already clean)")
        db.close()
    except Exception as e:
        print(f"  ⚠ Cleanup error: {e}")


def main():
    global passed, failed

    print("=" * 72)
    print("BACKUP & RESTORE v7.0 — COMPREHENSIVE TEST")
    print("=" * 72)
    print(f"API: {BASE_URL}")
    print(f"Demo user: {DEMO_USER['username']}")
    print(f"Temp user: {TEMP_USER['username']}")
    print()

    demo_api = APIClient()
    temp_api = APIClient()

    try:
        # ── Step 1: Login as demo user ────────────────────────────────────
        print("STEP 1: Login as demo user")
        demo_api.login(DEMO_USER["username"], DEMO_USER["password"])
        ok("Demo user logged in")
        print()

        # ── Step 2: Export demo user portfolio ────────────────────────────
        print("STEP 2: Export demo user portfolio")
        export_resp = demo_api.get("/portfolio/export")
        export_resp.raise_for_status()
        source_payload = export_resp.json()
        ok("Export successful")

        # Save to file for inspection
        export_file = f"/tmp/portact_backup_v7_test_{UNIQUE}.json"
        with open(export_file, "w") as f:
            json.dump(source_payload, f, indent=2)
        ok(f"Export saved to {export_file}")

        # ── Step 3: Verify export structure ───────────────────────────────
        print("\nSTEP 3: Verify export structure and data")
        verify_export_structure(source_payload)
        verify_export_counts(source_payload)

        # ── Step 4: Register temp user and restore ────────────────────────
        print("\nSTEP 4: Register temp user and restore backup")
        temp_api.register(TEMP_USER)
        ok("Temp user registered")
        temp_api.login(TEMP_USER["username"], TEMP_USER["password"])
        ok("Temp user logged in")

        with open(export_file, "rb") as f:
            restore_resp = temp_api.post(
                "/portfolio/restore",
                files={"file": ("backup.json", f, "application/json")},
            )
        restore_resp.raise_for_status()
        restore_data = restore_resp.json()

        if restore_data.get("success"):
            ok("Restore reported success")
        else:
            fail("Restore", str(restore_data))

        # Print restore stats
        print("\n── Restore Stats ──")
        stats = restore_data.get("stats", {})
        total_imported = 0
        total_skipped = 0
        for entity, counts in sorted(stats.items()):
            imp = counts.get("imported", 0)
            skp = counts.get("skipped", 0)
            total_imported += imp
            total_skipped += skp
            status_str = f"{imp} imported, {skp} skipped"
            if imp > 0:
                ok(f"{entity}: {status_str}")
            elif skp > 0:
                print(f"  · {entity}: {status_str}")
            else:
                print(f"  · {entity}: {status_str}")
        ok(f"TOTAL: {total_imported} imported, {total_skipped} skipped")

        # ── Step 5: Export from temp user and compare ─────────────────────
        print("\nSTEP 5: Export from temp user and compare")
        target_export = temp_api.get("/portfolio/export")
        target_export.raise_for_status()
        target_payload = target_export.json()
        ok("Temp user export successful")

        compare_exports(source_payload, target_payload)

        # ── Step 6: Idempotency — restore again ──────────────────────────
        print("\nSTEP 6: Idempotency — restore same backup again")
        with open(export_file, "rb") as f:
            idem_resp = temp_api.post(
                "/portfolio/restore",
                files={"file": ("backup.json", f, "application/json")},
            )
        idem_resp.raise_for_status()
        idem_data = idem_resp.json()
        if idem_data.get("success"):
            ok("Second restore reported success")
        else:
            fail("Second restore", str(idem_data))

        verify_idempotency(idem_data.get("stats", {}))

    except requests.HTTPError as e:
        fail("HTTP error", f"{e.response.status_code}: {e.response.text[:500]}")
        traceback.print_exc()
    except Exception as e:
        fail("Unexpected error", str(e))
        traceback.print_exc()
    finally:
        # ── Step 7: Cleanup ───────────────────────────────────────────────
        print("\nSTEP 7: Cleanup")
        cleanup_temp_user()
        print()

    # ── Summary ───────────────────────────────────────────────────────────
    print("=" * 72)
    if failed == 0:
        print(f"✅ ALL PASSED: {passed} checks passed, 0 failed")
    else:
        print(f"❌ RESULTS: {passed} passed, {failed} failed")
        print("\nFailed checks:")
        for e in errors:
            print(f"  {e}")
    print("=" * 72)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
