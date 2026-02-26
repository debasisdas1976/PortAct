import enum
from enum import auto

from sqlalchemy import Enum as _SAEnum, String
from sqlalchemy.types import TypeDecorator


class UpperStrEnum(str, enum.Enum):
    """Base enum where value is the lowercase form of the member name.

    Usage:
        class MyEnum(UpperStrEnum):
            FOO = auto()       # .value == "foo"
            BAR_BAZ = auto()   # .value == "bar_baz"

    Member names stay UPPERCASE (Python convention), but .value is
    always lowercase, matching the asset_type_master table, seed data,
    and frontend expectations.

    Includes case-insensitive lookup via _missing_ for backward
    compatibility with existing UPPERCASE DB rows or old export files.
    """

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if member.value.casefold() == str(value).casefold():
                return member
        return None


class SnapshotSource(UpperStrEnum):
    """Discriminator for AssetSnapshot rows — identifies the source entity."""
    ASSET = auto()           # "asset"  — real asset (FK via asset_id)
    BANK_ACCOUNT = auto()    # "bank_account" — bank account balance (FK via bank_account_id)
    DEMAT_CASH = auto()      # "demat_cash" — demat account cash (FK via demat_account_id)
    CRYPTO_CASH = auto()     # "crypto_cash" — crypto account cash (FK via crypto_account_id)


def LowerEnum(enum_class, **kw):
    """SQLAlchemy Enum type that uses .value (lowercase) for DB storage.

    SQLAlchemy's default Enum() uses .name for str-based enums, which
    is UPPERCASE.  This helper forces it to use .value instead, keeping
    DB labels lowercase and consistent with the rest of the stack.
    """
    kw.setdefault("values_callable", lambda cls: [e.value for e in cls])
    return _SAEnum(enum_class, **kw)


class LowerEnumStr(TypeDecorator):
    """SQLAlchemy type that stores enum values as VARCHAR but returns Python enum instances.

    Unlike LowerEnum (which creates a PG native enum type), this stores
    values as plain VARCHAR strings. This makes the column compatible with
    foreign key constraints to other VARCHAR columns (e.g., asset_types.name).

    Python-side behaviour is identical to LowerEnum: application code receives
    enum instances and can compare them normally (asset.asset_type == AssetType.STOCK).
    """

    impl = String(50)
    cache_ok = True

    def __init__(self, enum_class):
        self.enum_class = enum_class
        super().__init__()

    def process_bind_param(self, value, dialect):
        """Convert Python enum → lowercase string for DB storage."""
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value.value
        return str(value)

    def process_result_value(self, value, dialect):
        """Convert DB string → Python enum instance."""
        if value is None:
            return None
        return self.enum_class(value)
