import enum

from sqlalchemy import Enum as _SAEnum


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


def LowerEnum(enum_class, **kw):
    """SQLAlchemy Enum type that uses .value (lowercase) for DB storage.

    SQLAlchemy's default Enum() uses .name for str-based enums, which
    is UPPERCASE.  This helper forces it to use .value instead, keeping
    DB labels lowercase and consistent with the rest of the stack.
    """
    kw.setdefault("values_callable", lambda cls: [e.value for e in cls])
    return _SAEnum(enum_class, **kw)
