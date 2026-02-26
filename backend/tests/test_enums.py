"""Ensure all model enums use UpperStrEnum and have value == name.

This prevents case-mismatch bugs where the Python enum value differs
from what the frontend sends or what the database stores.
"""
import enum
import inspect

import app.models as models
from app.core.enums import UpperStrEnum


def _all_model_enums():
    """Collect every enum class exported from app.models."""
    return [
        getattr(models, name)
        for name in models.__all__
        if inspect.isclass(getattr(models, name))
        and issubclass(getattr(models, name), enum.Enum)
    ]


def test_all_model_enums_inherit_upper_str_enum():
    """Every enum in app.models must inherit from UpperStrEnum."""
    for cls in _all_model_enums():
        assert issubclass(cls, UpperStrEnum), (
            f"{cls.__name__} must inherit from UpperStrEnum, not plain enum.Enum"
        )


def test_enum_values_match_names():
    """Every enum member's .value must equal its .name lowercased."""
    for cls in _all_model_enums():
        for member in cls:
            assert member.value == member.name.lower(), (
                f"{cls.__name__}.{member.name} has value '{member.value}' "
                f"but should be '{member.name.lower()}'"
            )


def test_case_insensitive_lookup():
    """UpperStrEnum._missing_ allows case-insensitive lookups."""
    for cls in _all_model_enums():
        first = next(iter(cls))
        assert cls(first.value.lower()) is first
        assert cls(first.value.upper()) is first
