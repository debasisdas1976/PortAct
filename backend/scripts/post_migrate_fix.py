#!/usr/bin/env python3
"""
PortAct — Post-Migration Data Fix (v1.2.0)

Fixes known data issues that migrations cannot retroactively correct:

1. Vested/INDMoney demat accounts may have account_market='domestic'
   instead of 'international' due to a case-sensitive comparison in
   migration e5f6g7h8i9j0.

Usage:
    cd backend
    python scripts/post_migrate_fix.py

Safe to run multiple times (idempotent).
"""

import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from sqlalchemy import create_engine, text


def main():
    print("PortAct — Post-Migration Data Fix")
    print("=" * 40)

    engine = create_engine(settings.DATABASE_URL)

    with engine.begin() as conn:
        # ── Fix 1: Vested/INDMoney demat account market ──────────────
        #
        # Migration e5f6g7h8i9j0 used UPPERCASE comparison:
        #   WHERE broker_name::text IN ('VESTED', 'INDMONEY')
        # But broker_name may have been stored as lowercase, so the
        # UPDATE silently affected 0 rows. Fix it now.

        result = conn.execute(text(
            "UPDATE demat_accounts "
            "SET account_market = 'international' "
            "WHERE LOWER(broker_name) IN ('vested', 'indmoney') "
            "AND account_market = 'domestic'"
        ))
        fixed_count = result.rowcount

        if fixed_count > 0:
            print(f"  [FIXED] {fixed_count} Vested/INDMoney demat account(s) "
                  f"updated to account_market='international'")
        else:
            print("  [OK] No Vested/INDMoney accounts need fixing")

        # ── Verify: Asset types table is populated ───────────────────

        row = conn.execute(text(
            "SELECT COUNT(*) FROM asset_types"
        )).scalar()
        print(f"  [OK] asset_types table has {row} entries")

        # ── Verify: No orphan asset_type values ─────────────────────

        orphans = conn.execute(text(
            "SELECT DISTINCT a.asset_type FROM assets a "
            "LEFT JOIN asset_types at ON a.asset_type = at.name "
            "WHERE at.name IS NULL"
        )).fetchall()

        if orphans:
            orphan_types = [r[0] for r in orphans]
            print(f"  [WARNING] Found assets with unrecognized types: {orphan_types}")
            print("            These assets may not display correctly.")
        else:
            print("  [OK] All asset types have matching entries in asset_types table")

        # ── Verify: Snapshot source column exists and is populated ───

        try:
            snap_counts = conn.execute(text(
                "SELECT snapshot_source, COUNT(*) "
                "FROM asset_snapshots "
                "GROUP BY snapshot_source "
                "ORDER BY snapshot_source"
            )).fetchall()

            if snap_counts:
                print("  [OK] Snapshot sources:")
                for source, count in snap_counts:
                    print(f"        {source}: {count} rows")
            else:
                print("  [OK] No snapshot data yet (will populate on next EOD)")
        except Exception:
            print("  [INFO] snapshot_source column not found — "
                  "run 'alembic upgrade head' first")

    print()
    print("Data fix complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
