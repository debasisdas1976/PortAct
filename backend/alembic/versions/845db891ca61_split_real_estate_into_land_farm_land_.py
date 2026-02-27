"""Split real_estate into land farm_land house

Revision ID: 845db891ca61
Revises: dec2109f9419
Create Date: 2026-02-27 12:09:03.786608

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '845db891ca61'
down_revision = 'dec2109f9419'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Insert new asset_types (land, farm_land, house)
    conn.execute(sa.text("""
        INSERT INTO asset_types (name, display_label, category, sort_order, is_active)
        VALUES ('land', 'Land', 'Real Estate', 50, true)
        ON CONFLICT (name) DO NOTHING
    """))
    conn.execute(sa.text("""
        INSERT INTO asset_types (name, display_label, category, sort_order, is_active)
        VALUES ('farm_land', 'Farm Land', 'Real Estate', 51, true)
        ON CONFLICT (name) DO NOTHING
    """))
    conn.execute(sa.text("""
        INSERT INTO asset_types (name, display_label, category, sort_order, is_active)
        VALUES ('house', 'House', 'Real Estate', 52, true)
        ON CONFLICT (name) DO NOTHING
    """))

    # 2. Migrate existing real_estate assets to their specific sub-type
    #    based on details->>'property_type'
    for prop_type in ('land', 'farm_land', 'house'):
        conn.execute(sa.text("""
            UPDATE assets
            SET asset_type = :new_type
            WHERE asset_type = 'real_estate'
              AND LOWER(details->>'property_type') = :prop_type
        """), {"new_type": prop_type, "prop_type": prop_type})

    # 3. Any remaining real_estate assets without a valid property_type default to 'land'
    conn.execute(sa.text("""
        UPDATE assets
        SET asset_type = 'land'
        WHERE asset_type = 'real_estate'
    """))

    # 4. Remove old real_estate entry from asset_types master table
    conn.execute(sa.text("""
        DELETE FROM asset_types WHERE name = 'real_estate'
    """))


def downgrade() -> None:
    conn = op.get_bind()

    # Reverse: merge land/farm_land/house back into real_estate
    conn.execute(sa.text("""
        INSERT INTO asset_types (name, display_label, category, sort_order, is_active)
        VALUES ('real_estate', 'Real Estate', 'Real Estate', 50, true)
        ON CONFLICT (name) DO NOTHING
    """))

    for prop_type in ('land', 'farm_land', 'house'):
        conn.execute(sa.text("""
            UPDATE assets
            SET asset_type = 'real_estate'
            WHERE asset_type = :prop_type
        """), {"prop_type": prop_type})

    for prop_type in ('land', 'farm_land', 'house'):
        conn.execute(sa.text("""
            DELETE FROM asset_types WHERE name = :prop_type
        """), {"prop_type": prop_type})
