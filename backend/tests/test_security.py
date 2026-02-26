"""Unit tests for app.core.security — password hashing and JWT tokens."""
import pytest
from datetime import timedelta
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
)


@pytest.mark.unit
class TestPasswordHashing:
    def test_hash_and_verify_password(self):
        hashed = get_password_hash("SecurePassword123!")
        assert verify_password("SecurePassword123!", hashed)

    def test_verify_wrong_password(self):
        hashed = get_password_hash("CorrectPassword")
        assert not verify_password("WrongPassword", hashed)

    def test_password_truncation_at_72_bytes(self):
        """bcrypt silently truncates at 72 bytes; both strings should hash the same."""
        long_pw = "A" * 100
        hashed = get_password_hash(long_pw)
        # First 72 bytes match, so verification should succeed
        assert verify_password("A" * 100, hashed)
        assert verify_password("A" * 72, hashed)


@pytest.mark.unit
class TestJWTTokens:
    def test_create_access_token_has_expected_claims(self):
        token = create_access_token(data={"sub": "testuser", "user_id": 1})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 1
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_refresh_token_type_is_refresh(self):
        token = create_refresh_token(data={"sub": "testuser", "user_id": 1})
        payload = decode_token(token)
        assert payload is not None
        assert payload["type"] == "refresh"

    def test_decode_valid_token_roundtrip(self):
        token = create_access_token(data={"sub": "alice"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "alice"

    def test_decode_invalid_token_returns_none(self):
        assert decode_token("this.is.garbage") is None

    def test_decode_expired_token_returns_none(self):
        token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(minutes=-1),
        )
        assert decode_token(token) is None

    def test_access_token_custom_expiry(self):
        token = create_access_token(
            data={"sub": "testuser"},
            expires_delta=timedelta(minutes=60),
        )
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
