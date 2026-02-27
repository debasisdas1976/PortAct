"""API tests for asset endpoints (/api/v1/assets/*).

Covers full CRUD lifecycle for all 32 supported asset types.
"""
import pytest
from app.models.asset import AssetType
from app.models.crypto_account import CryptoAccount
from tests.conftest import make_asset


# ---------------------------------------------------------------------------
# All 32 asset types, grouped by behaviour
# ---------------------------------------------------------------------------

# Types that can be created with just asset_type + name (no special FK needed)
SIMPLE_TYPES = [
    AssetType.STOCK,
    AssetType.US_STOCK,
    AssetType.EQUITY_MUTUAL_FUND,
    AssetType.HYBRID_MUTUAL_FUND,
    AssetType.DEBT_MUTUAL_FUND,
    AssetType.COMMODITY,
    AssetType.CASH,
    AssetType.REIT,
    AssetType.INVIT,
    AssetType.SOVEREIGN_GOLD_BOND,
    AssetType.ESOP,
    AssetType.RSU,
    AssetType.SAVINGS_ACCOUNT,
    AssetType.RECURRING_DEPOSIT,
    AssetType.FIXED_DEPOSIT,
    AssetType.LAND,
    AssetType.FARM_LAND,
    AssetType.HOUSE,
    AssetType.PPF,
    AssetType.PF,
    AssetType.NPS,
    AssetType.SSY,
    AssetType.INSURANCE_POLICY,
    AssetType.GRATUITY,
    AssetType.NSC,
    AssetType.KVP,
    AssetType.SCSS,
    AssetType.MIS,
    AssetType.CORPORATE_BOND,
    AssetType.RBI_BOND,
    AssetType.TAX_SAVING_BOND,
]

# CRYPTO requires crypto_account_id — tested separately
ALL_TYPES = SIMPLE_TYPES + [AssetType.CRYPTO]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_crypto_account(db, user, portfolio_id):
    """Create a CryptoAccount in the DB for crypto-asset tests."""
    acct = CryptoAccount(
        user_id=user.id,
        portfolio_id=portfolio_id,
        exchange_name="WazirX",
        account_id="WXTEST001",
    )
    db.add(acct)
    db.flush()
    return acct


# ═══════════════════════════════════════════════════════════════════════════
# 1. Listing
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestAssetList:
    def test_list_assets_empty(self, auth_client):
        resp = auth_client.get("/api/v1/assets/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_assets_with_data(self, auth_client, db, test_user):
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        pid = portfolios[0]["id"]
        make_asset(db, test_user, pid, name="Stock A")
        make_asset(db, test_user, pid, name="Stock B")
        db.commit()

        resp = auth_client.get("/api/v1/assets/")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# ═══════════════════════════════════════════════════════════════════════════
# 2. Create — parametrised over every simple type
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestAssetCreateAllTypes:
    """Create each of the 31 simple asset types via the API."""

    @pytest.mark.parametrize("asset_type", SIMPLE_TYPES, ids=lambda t: t.value)
    def test_create_asset(self, auth_client, asset_type):
        payload = {
            "asset_type": asset_type.value,
            "name": f"Test {asset_type.name}",
            "quantity": 10,
            "purchase_price": 100.0,
            "total_invested": 1000.0,
            "current_price": 110.0,
        }
        resp = auth_client.post("/api/v1/assets/", json=payload)
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["asset_type"] == asset_type.value
        assert data["name"] == f"Test {asset_type.name}"
        assert data["portfolio_id"] is not None  # auto-assigned

    def test_create_crypto_with_account(self, auth_client, db, test_user):
        """CRYPTO requires crypto_account_id — should succeed when provided."""
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        pid = portfolios[0]["id"]
        acct = _create_crypto_account(db, test_user, pid)
        db.commit()

        resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "crypto",
            "name": "Bitcoin",
            "symbol": "BTC",
            "quantity": 0.5,
            "purchase_price": 50000.0,
            "total_invested": 25000.0,
            "current_price": 55000.0,
            "crypto_account_id": acct.id,
        })
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["asset_type"] == "crypto"
        assert data["crypto_account_id"] == acct.id

    def test_create_crypto_without_account_rejected(self, auth_client):
        """CRYPTO without crypto_account_id should be rejected."""
        resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "crypto",
            "name": "Bitcoin",
            "symbol": "BTC",
            "quantity": 0.5,
        })
        assert resp.status_code == 400
        assert "crypto account" in resp.json()["detail"].lower()


# ═══════════════════════════════════════════════════════════════════════════
# 3. Create — validation & auto-assignment
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestAssetCreateValidation:
    def test_auto_assigns_default_portfolio(self, auth_client):
        resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "ppf",
            "name": "My PPF",
            "quantity": 1,
        })
        assert resp.status_code == 201
        assert resp.json()["portfolio_id"] is not None

    def test_metrics_calculated_on_create(self, auth_client):
        """profit_loss and profit_loss_percentage are computed server-side."""
        resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "stock",
            "name": "Metrics Test",
            "quantity": 10,
            "purchase_price": 100.0,
            "current_price": 120.0,
            "total_invested": 1000.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["current_value"] == 1200.0
        assert data["profit_loss"] == 200.0
        assert data["profit_loss_percentage"] == 20.0

    def test_negative_quantity_rejected(self, auth_client):
        """quantity must be >= 0."""
        resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "stock",
            "name": "Bad",
            "quantity": -5,
        })
        assert resp.status_code == 422  # Pydantic validation

    def test_missing_name_rejected(self, auth_client):
        resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "stock",
        })
        assert resp.status_code == 422

    def test_missing_asset_type_rejected(self, auth_client):
        resp = auth_client.post("/api/v1/assets/", json={
            "name": "No Type",
        })
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# 4. Full CRUD lifecycle — parametrised over every type
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestAssetCRUDLifecycle:
    """Create → Read → Update → Delete for every simple asset type."""

    @pytest.mark.parametrize("asset_type", SIMPLE_TYPES, ids=lambda t: t.value)
    def test_crud_lifecycle(self, auth_client, asset_type):
        # ── CREATE ──
        payload = {
            "asset_type": asset_type.value,
            "name": f"CRUD {asset_type.name}",
            "quantity": 5,
            "purchase_price": 200.0,
            "current_price": 200.0,
            "total_invested": 1000.0,
        }
        create_resp = auth_client.post("/api/v1/assets/", json=payload)
        assert create_resp.status_code == 201, create_resp.text
        asset_id = create_resp.json()["id"]

        # ── READ ──
        get_resp = auth_client.get(f"/api/v1/assets/{asset_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["asset_type"] == asset_type.value
        assert get_resp.json()["name"] == f"CRUD {asset_type.name}"

        # ── UPDATE ──
        update_resp = auth_client.put(f"/api/v1/assets/{asset_id}", json={
            "current_price": 250.0,
            "notes": "Updated in test",
        })
        assert update_resp.status_code == 200
        updated = update_resp.json()
        assert updated["current_price"] == 250.0
        assert updated["notes"] == "Updated in test"

        # ── DELETE ──
        del_resp = auth_client.delete(f"/api/v1/assets/{asset_id}")
        assert del_resp.status_code == 204
        # Verify deletion
        gone_resp = auth_client.get(f"/api/v1/assets/{asset_id}")
        assert gone_resp.status_code == 404

    def test_crud_lifecycle_crypto(self, auth_client, db, test_user):
        """Crypto needs a crypto_account — test the full lifecycle separately."""
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        pid = portfolios[0]["id"]
        acct = _create_crypto_account(db, test_user, pid)
        db.commit()

        # CREATE
        create_resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "crypto",
            "name": "Ethereum",
            "symbol": "ETH",
            "quantity": 2,
            "purchase_price": 150000.0,
            "current_price": 160000.0,
            "total_invested": 300000.0,
            "crypto_account_id": acct.id,
        })
        assert create_resp.status_code == 201, create_resp.text
        asset_id = create_resp.json()["id"]

        # READ
        get_resp = auth_client.get(f"/api/v1/assets/{asset_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["asset_type"] == "crypto"

        # UPDATE
        update_resp = auth_client.put(f"/api/v1/assets/{asset_id}", json={
            "current_price": 170000.0,
        })
        assert update_resp.status_code == 200
        assert update_resp.json()["current_price"] == 170000.0

        # DELETE
        del_resp = auth_client.delete(f"/api/v1/assets/{asset_id}")
        assert del_resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════
# 5. Read — edge cases
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestAssetRead:
    def test_get_nonexistent_asset(self, auth_client):
        resp = auth_client.get("/api/v1/assets/99999")
        assert resp.status_code == 404

    def test_response_contains_computed_fields(self, auth_client):
        """Verify the response includes all server-computed fields."""
        resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "fixed_deposit",
            "name": "FD Response Check",
            "quantity": 1,
            "purchase_price": 100000.0,
            "current_price": 107000.0,
            "total_invested": 100000.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        expected_fields = {
            "id", "asset_type", "name", "quantity", "purchase_price",
            "current_price", "total_invested", "current_value",
            "profit_loss", "profit_loss_percentage", "is_active",
            "portfolio_id", "created_at",
        }
        assert expected_fields.issubset(set(data.keys()))


# ═══════════════════════════════════════════════════════════════════════════
# 6. Update — edge cases
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestAssetUpdate:
    def test_update_nonexistent_asset(self, auth_client):
        resp = auth_client.put("/api/v1/assets/99999", json={"name": "Ghost"})
        assert resp.status_code == 404

    def test_partial_update_preserves_other_fields(self, auth_client):
        create_resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "ppf",
            "name": "PPF Partial",
            "quantity": 1,
            "purchase_price": 50000.0,
            "total_invested": 50000.0,
            "notes": "original note",
        })
        asset_id = create_resp.json()["id"]

        # Update only current_price
        update_resp = auth_client.put(f"/api/v1/assets/{asset_id}", json={
            "current_price": 55000.0,
        })
        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["current_price"] == 55000.0
        assert data["name"] == "PPF Partial"
        assert data["notes"] == "original note"

    def test_deactivate_asset(self, auth_client):
        create_resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "nps",
            "name": "NPS Deactivate",
            "quantity": 1,
        })
        asset_id = create_resp.json()["id"]

        resp = auth_client.put(f"/api/v1/assets/{asset_id}", json={
            "is_active": False,
        })
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_metrics_recalculated_on_update(self, auth_client):
        create_resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "stock",
            "name": "Recalc Test",
            "quantity": 10,
            "purchase_price": 100.0,
            "current_price": 100.0,
            "total_invested": 1000.0,
        })
        asset_id = create_resp.json()["id"]

        resp = auth_client.put(f"/api/v1/assets/{asset_id}", json={
            "current_price": 150.0,
        })
        data = resp.json()
        # 10 * 150 = 1500 current_value, profit = 500, pct = 50%
        assert data["current_value"] == 1500.0
        assert data["profit_loss"] == 500.0
        assert data["profit_loss_percentage"] == 50.0


# ═══════════════════════════════════════════════════════════════════════════
# 7. Delete — edge cases
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestAssetDelete:
    def test_delete_nonexistent_asset(self, auth_client):
        resp = auth_client.delete("/api/v1/assets/99999")
        assert resp.status_code == 404

    def test_delete_is_permanent(self, auth_client):
        create_resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "gratuity",
            "name": "Gratuity Delete",
            "quantity": 1,
        })
        asset_id = create_resp.json()["id"]
        auth_client.delete(f"/api/v1/assets/{asset_id}")

        # Not in list either
        list_resp = auth_client.get("/api/v1/assets/")
        ids = [a["id"] for a in list_resp.json()]
        assert asset_id not in ids


# ═══════════════════════════════════════════════════════════════════════════
# 8. Filtering — parametrised over every type
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestAssetFiltering:
    @pytest.mark.parametrize("asset_type", SIMPLE_TYPES, ids=lambda t: t.value)
    def test_filter_by_asset_type(self, auth_client, db, test_user, asset_type):
        """Create two different types, filter, and verify only the target returns."""
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        pid = portfolios[0]["id"]

        # Create the target asset and one different type to ensure filtering works
        make_asset(db, test_user, pid, name=f"Target {asset_type.name}",
                   asset_type=asset_type)
        # Pick a contrasting type
        other = AssetType.PPF if asset_type != AssetType.PPF else AssetType.STOCK
        make_asset(db, test_user, pid, name="Other", asset_type=other)
        db.commit()

        resp = auth_client.get("/api/v1/assets/",
                               params={"asset_type": asset_type.value})
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1
        assert all(a["asset_type"] == asset_type.value for a in results)

    def test_filter_by_portfolio_id(self, auth_client, db, test_user):
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        default_pid = portfolios[0]["id"]

        p2_resp = auth_client.post("/api/v1/portfolios/", json={"name": "P2"})
        p2_id = p2_resp.json()["id"]
        make_asset(db, test_user, default_pid, name="InDefault")
        make_asset(db, test_user, p2_id, name="InP2")
        db.commit()

        resp = auth_client.get("/api/v1/assets/", params={"portfolio_id": p2_id})
        assert resp.status_code == 200
        assert all(a["portfolio_id"] == p2_id for a in resp.json())

    def test_filter_active_only(self, auth_client, db, test_user):
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        pid = portfolios[0]["id"]
        make_asset(db, test_user, pid, name="Active", is_active=True)
        make_asset(db, test_user, pid, name="Inactive", is_active=False)
        db.commit()

        resp = auth_client.get("/api/v1/assets/", params={"is_active": True})
        assert resp.status_code == 200
        assert all(a["is_active"] for a in resp.json())


# ═══════════════════════════════════════════════════════════════════════════
# 9. Summary — multiple types
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestAssetSummary:
    def test_portfolio_summary(self, auth_client, db, test_user):
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        pid = portfolios[0]["id"]
        make_asset(db, test_user, pid, name="A1", total_invested=1000.0,
                   current_value=1200.0, quantity=10, current_price=120.0)
        make_asset(db, test_user, pid, name="A2", total_invested=2000.0,
                   current_value=2500.0, quantity=20, current_price=125.0)
        db.commit()

        resp = auth_client.get("/api/v1/assets/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_assets"] == 2
        assert data["total_invested"] > 0

    def test_summary_with_multiple_types(self, auth_client, db, test_user):
        """Summary aggregates across different asset types."""
        portfolios = auth_client.get("/api/v1/portfolios/").json()
        pid = portfolios[0]["id"]
        make_asset(db, test_user, pid, name="S1", asset_type=AssetType.STOCK,
                   total_invested=5000.0, current_value=5500.0,
                   quantity=10, current_price=550.0)
        make_asset(db, test_user, pid, name="FD1", asset_type=AssetType.FIXED_DEPOSIT,
                   total_invested=10000.0, current_value=10700.0,
                   quantity=1, current_price=10700.0)
        make_asset(db, test_user, pid, name="PPF1", asset_type=AssetType.PPF,
                   total_invested=15000.0, current_value=16000.0,
                   quantity=1, current_price=16000.0)
        db.commit()

        resp = auth_client.get("/api/v1/assets/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_assets"] == 3
        assert data["total_invested"] == 30000.0


# ═══════════════════════════════════════════════════════════════════════════
# 10. Type-specific behaviour
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.api
class TestAssetTypeSpecific:
    """Tests for type-specific business logic."""

    def test_esop_created_with_details(self, auth_client):
        resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "esop",
            "name": "Company ESOP",
            "symbol": "COMP",
            "quantity": 100,
            "purchase_price": 50.0,
            "current_price": 80.0,
            "total_invested": 5000.0,
            "details": {"vesting_schedule": "4yr cliff", "grant_date": "2024-01-01"},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["asset_type"] == "esop"
        assert data["details"]["vesting_schedule"] == "4yr cliff"

    def test_rsu_created_with_details(self, auth_client):
        resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "rsu",
            "name": "Company RSU",
            "symbol": "COMP",
            "quantity": 50,
            "purchase_price": 0.0,
            "current_price": 120.0,
            "total_invested": 0.0,
            "details": {"vest_date": "2025-03-15"},
        })
        assert resp.status_code == 201
        assert resp.json()["asset_type"] == "rsu"

    def test_real_estate_types_with_details(self, auth_client):
        """All three real estate types (land, farm_land, house) should create successfully."""
        for re_type, prop_name in [
            ("land", "Plot in Pune"),
            ("farm_land", "Farm in Kerala"),
            ("house", "Mumbai Flat"),
        ]:
            resp = auth_client.post("/api/v1/assets/", json={
                "asset_type": re_type,
                "name": prop_name,
                "quantity": 1,
                "purchase_price": 5000000.0,
                "current_price": 6000000.0,
                "total_invested": 5000000.0,
                "details": {"property_type": re_type, "area_sqft": 1200},
            })
            assert resp.status_code == 201, f"Failed for {re_type}: {resp.text}"
            data = resp.json()
            assert data["asset_type"] == re_type
            assert data["current_value"] == 6000000.0

    def test_fixed_deposit_with_details(self, auth_client):
        resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "fixed_deposit",
            "name": "HDFC FD",
            "quantity": 1,
            "purchase_price": 100000.0,
            "current_price": 107000.0,
            "total_invested": 100000.0,
            "details": {"bank_name": "HDFC", "interest_rate": 7.0,
                        "maturity_date": "2026-12-31"},
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["details"]["interest_rate"] == 7.0

    def test_insurance_policy_with_details(self, auth_client):
        resp = auth_client.post("/api/v1/assets/", json={
            "asset_type": "insurance_policy",
            "name": "LIC Endowment",
            "quantity": 1,
            "purchase_price": 50000.0,
            "total_invested": 50000.0,
            "details": {"policy_number": "LIC123", "premium": 5000,
                        "sum_assured": 500000},
        })
        assert resp.status_code == 201
        assert resp.json()["details"]["policy_number"] == "LIC123"

    def test_mutual_fund_types(self, auth_client):
        """All three mutual fund types should work identically."""
        for mf_type in ["equity_mutual_fund", "hybrid_mutual_fund",
                        "debt_mutual_fund"]:
            resp = auth_client.post("/api/v1/assets/", json={
                "asset_type": mf_type,
                "name": f"Test {mf_type}",
                "symbol": "ABCMF",
                "isin": "INF123456789",
                "quantity": 100,
                "purchase_price": 50.0,
                "current_price": 55.0,
                "total_invested": 5000.0,
            })
            assert resp.status_code == 201, f"Failed for {mf_type}: {resp.text}"
            assert resp.json()["asset_type"] == mf_type

    def test_bond_types(self, auth_client):
        """All bond-like types should create successfully."""
        for bond_type in ["corporate_bond", "rbi_bond", "tax_saving_bond",
                          "sovereign_gold_bond"]:
            resp = auth_client.post("/api/v1/assets/", json={
                "asset_type": bond_type,
                "name": f"Test {bond_type}",
                "quantity": 10,
                "purchase_price": 1000.0,
                "current_price": 1050.0,
                "total_invested": 10000.0,
            })
            assert resp.status_code == 201, f"Failed for {bond_type}: {resp.text}"

    def test_small_savings_types(self, auth_client):
        """Government small-savings schemes all follow the same pattern."""
        for ss_type in ["ppf", "nps", "ssy", "nsc", "kvp", "scss", "mis"]:
            resp = auth_client.post("/api/v1/assets/", json={
                "asset_type": ss_type,
                "name": f"Test {ss_type}",
                "quantity": 1,
                "total_invested": 10000.0,
                "current_price": 10500.0,
            })
            assert resp.status_code == 201, f"Failed for {ss_type}: {resp.text}"
