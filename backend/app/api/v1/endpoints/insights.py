from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import Optional
from datetime import date, timedelta
from collections import defaultdict

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.asset import Asset, AssetType
from app.models.asset_type_master import AssetTypeMaster
from app.models.transaction import Transaction
from app.models.portfolio_snapshot import AssetSnapshot
from app.models.bank_account import BankAccount
from app.models.demat_account import DematAccount
from app.models.crypto_account import CryptoAccount
from app.models.asset_attribute import AssetAttribute, AssetAttributeValue, AssetAttributeAssignment
from app.services.xirr_service import build_cash_flows_from_transactions, calculate_xirr

router = APIRouter()

# Known default interest rates for fixed-rate asset types
_DEFAULT_RATES = {
    AssetType.SSY: 8.2,
    AssetType.PF: 8.25,
    AssetType.PPF: 7.1,
}


@router.get("/category-allocation-xirr")
async def get_category_allocation_xirr(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Returns current value and investment-weighted XIRR per asset allocation category.
    """
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True,
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()

    # Build asset_type -> category map
    type_rows = db.query(AssetTypeMaster.name, AssetTypeMaster.category).all()
    type_to_category = {r.name: r.category for r in type_rows}

    for asset in assets:
        asset.calculate_metrics()
        if asset.xirr is None and not asset.xirr_manual:
            asset.xirr = asset.fallback_xirr()
            if asset.xirr is None and asset.asset_type in _DEFAULT_RATES:
                asset.xirr = _DEFAULT_RATES[asset.asset_type]

    # Group by category
    categories: dict = defaultdict(lambda: {
        "total_invested": 0.0,
        "current_value": 0.0,
        "weighted_xirr_sum": 0.0,
        "xirr_weight_total": 0.0,
        "asset_count": 0,
    })

    for asset in assets:
        cat = type_to_category.get(asset.asset_type.value, "Other")
        bucket = categories[cat]
        bucket["total_invested"] += asset.total_invested or 0
        bucket["current_value"] += asset.current_value or 0
        bucket["asset_count"] += 1

        if asset.xirr is not None:
            weight = (
                asset.total_invested
                if asset.total_invested and asset.total_invested > 0
                else (
                    asset.current_value
                    if asset.current_value and asset.current_value > 0
                    else 0
                )
            )
            if weight > 0:
                bucket["weighted_xirr_sum"] += asset.xirr * weight
                bucket["xirr_weight_total"] += weight

    result = []
    for cat, data in categories.items():
        xirr_val = (
            round(data["weighted_xirr_sum"] / data["xirr_weight_total"], 2)
            if data["xirr_weight_total"] > 0
            else None
        )
        result.append({
            "name": cat,
            "total_invested": round(data["total_invested"], 2),
            "current_value": round(data["current_value"], 2),
            "xirr": xirr_val,
            "asset_count": data["asset_count"],
        })

    # Sort by current_value descending
    result.sort(key=lambda x: x["current_value"], reverse=True)
    return {"categories": result}


@router.get("/category-performance-history")
async def get_category_performance_history(
    days: int = Query(default=90, ge=1, le=365),
    portfolio_id: Optional[int] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Returns historical performance time series aggregated by category from AssetSnapshot data.
    When `category` is provided, returns per-asset breakdown within that category.
    """
    start_date = date.today() - timedelta(days=days)

    # Build asset_type -> category map
    type_rows = db.query(AssetTypeMaster.name, AssetTypeMaster.category).all()
    type_to_category = {r.name: r.category for r in type_rows}
    # Reverse map: category -> list of asset_type names
    category_types = defaultdict(list)
    for name, cat in type_to_category.items():
        category_types[cat].append(name)

    # Base query: asset-sourced snapshots only
    base_q = (
        db.query(AssetSnapshot)
        .filter(
            AssetSnapshot.snapshot_source == "asset",
            AssetSnapshot.snapshot_date >= start_date,
            AssetSnapshot.asset_type.isnot(None),
        )
    )

    if portfolio_id is not None:
        # Filter via asset's portfolio_id
        base_q = base_q.join(Asset, AssetSnapshot.asset_id == Asset.id).filter(
            Asset.user_id == current_user.id,
            Asset.portfolio_id == portfolio_id,
        )
    else:
        base_q = base_q.join(Asset, AssetSnapshot.asset_id == Asset.id).filter(
            Asset.user_id == current_user.id,
        )

    if category is not None:
        # Drill-down: filter by specific category's asset types
        allowed_types = category_types.get(category, [])
        if not allowed_types:
            return {"period_days": days, "category": category, "data": []}
        base_q = base_q.filter(Asset.asset_type.in_(allowed_types))

        # Group by date + asset
        rows = (
            base_q.with_entities(
                AssetSnapshot.snapshot_date,
                AssetSnapshot.asset_id,
                AssetSnapshot.asset_name,
                func.sum(AssetSnapshot.total_invested).label("invested"),
                func.sum(AssetSnapshot.current_value).label("value"),
            )
            .group_by(
                AssetSnapshot.snapshot_date,
                AssetSnapshot.asset_id,
                AssetSnapshot.asset_name,
            )
            .order_by(AssetSnapshot.snapshot_date)
            .all()
        )

        # Pivot: date -> { asset_name: { invested, value } }
        # Multiple assets can share the same name (e.g. same fund in different accounts),
        # so accumulate values instead of overwriting.
        date_map: dict = defaultdict(lambda: defaultdict(lambda: {"invested": 0.0, "value": 0.0}))
        for row in rows:
            bucket = date_map[row.snapshot_date.isoformat()][row.asset_name]
            bucket["invested"] += round(row.invested or 0, 2)
            bucket["value"] += round(row.value or 0, 2)

        data = [{"date": d, "assets": dict(assets)} for d, assets in sorted(date_map.items())]
        return {"period_days": days, "category": category, "data": data}

    # Category-level aggregation — use asset's current type for categorisation
    snapshots = base_q.with_entities(
        AssetSnapshot.snapshot_date,
        AssetSnapshot.total_invested,
        AssetSnapshot.current_value,
        Asset.asset_type,
    ).all()

    date_map: dict = defaultdict(lambda: defaultdict(lambda: {"invested": 0.0, "value": 0.0}))
    for snap in snapshots:
        cat = type_to_category.get(snap.asset_type.value if hasattr(snap.asset_type, 'value') else snap.asset_type, "Other")
        bucket = date_map[snap.snapshot_date.isoformat()][cat]
        bucket["invested"] += snap.total_invested or 0
        bucket["value"] += snap.current_value or 0

    # Round values
    data = []
    for d in sorted(date_map.keys()):
        cats = {}
        for cat, vals in date_map[d].items():
            cats[cat] = {
                "invested": round(vals["invested"], 2),
                "value": round(vals["value"], 2),
            }
        data.append({"date": d, "categories": cats})

    return {"period_days": days, "data": data}


@router.get("/category-xirr-trend")
async def get_category_xirr_trend(
    days: int = Query(default=90, ge=1, le=365),
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Computes rolling XIRR for each category at weekly-sampled intervals.
    For each sample date, uses transactions up to that date and asset value
    from snapshots on that date.
    """
    start_date = date.today() - timedelta(days=days)

    # Build asset_type -> category map
    type_rows = db.query(AssetTypeMaster.name, AssetTypeMaster.category).all()
    type_to_category = {r.name: r.category for r in type_rows}

    # Get all active assets for user
    asset_q = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True,
    )
    if portfolio_id is not None:
        asset_q = asset_q.filter(Asset.portfolio_id == portfolio_id)
    assets = asset_q.all()

    if not assets:
        return {"period_days": days, "data": []}

    asset_ids = [a.id for a in assets]

    # Group assets by category
    cat_assets: dict = defaultdict(list)
    for asset in assets:
        cat = type_to_category.get(asset.asset_type.value, "Other")
        cat_assets[cat].append(asset)

    # Load all transactions for these assets (sorted by date)
    all_transactions = (
        db.query(Transaction)
        .filter(Transaction.asset_id.in_(asset_ids))
        .order_by(Transaction.transaction_date)
        .all()
    )

    # Group transactions by asset_id
    txn_by_asset: dict = defaultdict(list)
    for txn in all_transactions:
        txn_by_asset[txn.asset_id].append(txn)

    # Get asset snapshots in the date range
    snap_q = (
        db.query(AssetSnapshot)
        .filter(
            AssetSnapshot.snapshot_source == "asset",
            AssetSnapshot.asset_id.in_(asset_ids),
            AssetSnapshot.snapshot_date >= start_date,
        )
        .all()
    )

    # Index: (asset_id, date) -> current_value
    snap_values: dict = {}
    available_dates: set = set()
    for snap in snap_q:
        snap_values[(snap.asset_id, snap.snapshot_date)] = snap.current_value or 0
        available_dates.add(snap.snapshot_date)

    # Sample dates at weekly intervals
    sorted_dates = sorted(available_dates)
    if not sorted_dates:
        return {"period_days": days, "data": []}

    # Pick every 7th date (weekly sampling)
    if len(sorted_dates) <= 15:
        sample_dates = sorted_dates
    else:
        step = max(1, len(sorted_dates) // 15)
        sample_dates = sorted_dates[::step]
        # Always include the last date
        if sample_dates[-1] != sorted_dates[-1]:
            sample_dates.append(sorted_dates[-1])

    # Compute XIRR at each sample date for each category
    data = []
    for sample_date in sample_dates:
        cat_xirrs = {}
        for cat, cat_asset_list in cat_assets.items():
            # Aggregate: build combined cash flows for all assets in category
            combined_flows = []
            total_value = 0.0

            for asset in cat_asset_list:
                asset_txns = txn_by_asset.get(asset.id, [])
                # Filter transactions up to sample_date
                filtered_txns = [
                    t for t in asset_txns
                    if (t.transaction_date.date() if hasattr(t.transaction_date, 'date') else t.transaction_date) <= sample_date
                ]
                val = snap_values.get((asset.id, sample_date), 0)
                total_value += val

                flows = build_cash_flows_from_transactions(
                    filtered_txns, 0, sample_date  # Don't add terminal value per asset
                )
                combined_flows.extend(flows)

            # Add combined terminal value
            if total_value > 0:
                combined_flows.append((sample_date, total_value))

            xirr_val = calculate_xirr(combined_flows) if combined_flows else None
            if xirr_val is not None:
                cat_xirrs[cat] = round(xirr_val, 2)

        data.append({
            "date": sample_date.isoformat(),
            "categories": cat_xirrs,
        })

    return {"period_days": days, "data": data}


MATURITY_ASSET_TYPES = [
    AssetType.FIXED_DEPOSIT, AssetType.RECURRING_DEPOSIT,
    AssetType.CORPORATE_BOND, AssetType.RBI_BOND, AssetType.TAX_SAVING_BOND,
    AssetType.NSC, AssetType.KVP, AssetType.SCSS, AssetType.MIS,
    AssetType.INSURANCE_POLICY, AssetType.SOVEREIGN_GOLD_BOND,
    AssetType.PPF, AssetType.SSY,
]


@router.get("/maturity-timeline")
async def get_maturity_timeline(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Returns assets with maturity dates, sorted chronologically.
    Includes current value, interest rate, and calculated maturity amount.
    """
    query = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True,
        Asset.asset_type.in_([t.value for t in MATURITY_ASSET_TYPES]),
    )
    if portfolio_id is not None:
        query = query.filter(Asset.portfolio_id == portfolio_id)
    assets = query.all()

    today = date.today()
    items = []

    for asset in assets:
        asset.calculate_metrics()
        details = asset.details or {}
        if not isinstance(details, dict):
            continue

        maturity_str = details.get("maturity_date") or details.get("policy_end_date")
        if not maturity_str:
            continue

        try:
            maturity_dt = date.fromisoformat(str(maturity_str))
        except (ValueError, TypeError):
            continue

        days_remaining = (maturity_dt - today).days
        interest_rate = details.get("interest_rate")
        current_val = asset.current_value or 0

        # Estimate maturity amount
        # For insurance: use sum_assured as the maturity payout
        # For others: compound interest estimate from current value
        sum_assured = details.get("sum_assured")
        if sum_assured and asset.asset_type == AssetType.INSURANCE_POLICY:
            maturity_amount = round(sum_assured, 2)
        elif interest_rate and days_remaining > 0 and current_val > 0:
            years_left = days_remaining / 365.25
            maturity_amount = round(current_val * ((1 + interest_rate / 100) ** years_left), 2)
        else:
            maturity_amount = current_val

        # Determine status
        if days_remaining < 0:
            status = "Matured"
        elif days_remaining <= 180:
            status = "Maturing Soon"
        elif days_remaining <= 365:
            status = "Approaching"
        else:
            status = "On Track"

        items.append({
            "asset_id": asset.id,
            "asset_name": asset.name,
            "asset_type": asset.asset_type.value if hasattr(asset.asset_type, 'value') else asset.asset_type,
            "maturity_date": maturity_str,
            "days_remaining": days_remaining,
            "current_value": round(current_val, 2),
            "total_invested": round(asset.total_invested or 0, 2),
            "interest_rate": interest_rate,
            "maturity_amount": maturity_amount,
            "status": status,
        })

    # Sort: upcoming first, then matured at the end
    items.sort(key=lambda x: (x["days_remaining"] < 0, abs(x["days_remaining"])))

    return {"items": items, "total_count": len(items)}


@router.get("/attribute-allocation")
async def get_attribute_allocation(
    portfolio_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Returns current_value aggregated by each attribute's values.
    For each active attribute, produces a list of { label, color, current_value, asset_count }.
    Includes an 'Unassigned' bucket for assets without a value for that attribute.
    """
    # 1. Fetch all active assets
    asset_q = db.query(Asset).filter(
        Asset.user_id == current_user.id,
        Asset.is_active == True,
    )
    if portfolio_id is not None:
        asset_q = asset_q.filter(Asset.portfolio_id == portfolio_id)
    assets = asset_q.all()

    if not assets:
        return {"attributes": [], "total_portfolio_value": 0}

    for asset in assets:
        asset.calculate_metrics()

    asset_map = {a.id: a for a in assets}
    asset_ids = list(asset_map.keys())

    # 2. Fetch active attributes with values
    attributes = (
        db.query(AssetAttribute)
        .options(joinedload(AssetAttribute.values))
        .filter(
            AssetAttribute.user_id == current_user.id,
            AssetAttribute.is_active == True,
        )
        .order_by(AssetAttribute.sort_order, AssetAttribute.display_label)
        .all()
    )

    if not attributes:
        return {"attributes": [], "total_portfolio_value": 0}

    # 3. Fetch all assignments for these assets
    assignments = (
        db.query(AssetAttributeAssignment)
        .filter(AssetAttributeAssignment.asset_id.in_(asset_ids))
        .all()
    )

    # Index: (attribute_id, asset_id) -> attribute_value_id
    assign_map = {}
    for a in assignments:
        assign_map[(a.attribute_id, a.asset_id)] = a.attribute_value_id

    # 4. Build result per attribute
    total_portfolio_value = sum(a.current_value or 0 for a in assets)
    result = []

    for attr in attributes:
        value_map = {v.id: v for v in attr.values}
        buckets: dict = defaultdict(lambda: {"current_value": 0.0, "asset_count": 0})
        unassigned = {"current_value": 0.0, "asset_count": 0}

        for asset_id, asset in asset_map.items():
            val_id = assign_map.get((attr.id, asset_id))
            if val_id and val_id in value_map:
                buckets[val_id]["current_value"] += asset.current_value or 0
                buckets[val_id]["asset_count"] += 1
            else:
                unassigned["current_value"] += asset.current_value or 0
                unassigned["asset_count"] += 1

        values_data = []
        for v in sorted(attr.values, key=lambda x: x.sort_order):
            if not v.is_active:
                continue
            b = buckets.get(v.id, {"current_value": 0.0, "asset_count": 0})
            values_data.append({
                "label": v.label,
                "color": v.color,
                "current_value": round(b["current_value"], 2),
                "asset_count": b["asset_count"],
            })

        if unassigned["asset_count"] > 0:
            values_data.append({
                "label": "Unassigned",
                "color": "#9E9E9E",
                "current_value": round(unassigned["current_value"], 2),
                "asset_count": unassigned["asset_count"],
            })

        result.append({
            "attribute_id": attr.id,
            "attribute_name": attr.name,
            "display_label": attr.display_label,
            "icon": attr.icon,
            "values": values_data,
        })

    return {"attributes": result, "total_portfolio_value": round(total_portfolio_value, 2)}
