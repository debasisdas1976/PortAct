import enum


class UpperStrEnum(str, enum.Enum):
    """Base enum where value always equals the member name (UPPERCASE).

    Usage:
        class MyEnum(UpperStrEnum):
            FOO = auto()
            BAR = auto()

    This ensures MyEnum.FOO.value == "FOO" (never "foo"), preventing
    case mismatches between Python enums, Pydantic validation, the
    database, and the frontend.

    Includes case-insensitive lookup via _missing_ for backward
    compatibility with existing lowercase DB rows or frontend values.
    """

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if member.value.casefold() == str(value).casefold():
                return member
        return None
