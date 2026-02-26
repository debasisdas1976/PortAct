"""API tests for authentication endpoints (/api/v1/auth/*)."""
import pytest


@pytest.mark.api
class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "StrongPass1!",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "new@example.com"
        assert data["username"] == "newuser"
        assert "id" in data

    def test_register_duplicate_email(self, client):
        payload = {
            "email": "dup@example.com",
            "username": "user1",
            "full_name": "User",
            "password": "StrongPass1!",
        }
        client.post("/api/v1/auth/register", json=payload)
        payload["username"] = "user2"
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 400

    def test_register_duplicate_username(self, client):
        payload = {
            "email": "a@example.com",
            "username": "sameuser",
            "full_name": "User",
            "password": "StrongPass1!",
        }
        client.post("/api/v1/auth/register", json=payload)
        payload["email"] = "b@example.com"
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 400

    def test_register_short_password(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "x@example.com",
            "username": "xuser",
            "full_name": "X",
            "password": "short",
        })
        assert resp.status_code == 422

    def test_register_missing_fields(self, client):
        resp = client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 422


@pytest.mark.api
class TestLogin:
    def _register(self, client, username="loginuser", email="login@example.com"):
        client.post("/api/v1/auth/register", json={
            "email": email,
            "username": username,
            "full_name": "Login User",
            "password": "LoginPass1!",
        })

    def test_login_success(self, client):
        self._register(client)
        resp = client.post("/api/v1/auth/login", data={
            "username": "loginuser",
            "password": "LoginPass1!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client):
        self._register(client, username="wpuser", email="wp@example.com")
        resp = client.post("/api/v1/auth/login", data={
            "username": "wpuser",
            "password": "WrongPassword",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/v1/auth/login", data={
            "username": "ghost",
            "password": "Irrelevant1!",
        })
        assert resp.status_code == 401

    def test_login_by_email(self, client):
        self._register(client, username="emaillogin", email="elog@example.com")
        resp = client.post("/api/v1/auth/login", data={
            "username": "elog@example.com",
            "password": "LoginPass1!",
        })
        assert resp.status_code == 200


@pytest.mark.api
class TestTokenRefresh:
    def test_refresh_valid_token(self, client):
        client.post("/api/v1/auth/register", json={
            "email": "ref@example.com",
            "username": "refuser",
            "full_name": "Ref User",
            "password": "RefreshPass1!",
        })
        login_resp = client.post("/api/v1/auth/login", data={
            "username": "refuser",
            "password": "RefreshPass1!",
        })
        refresh_token = login_resp.json()["refresh_token"]
        resp = client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_invalid_token(self, client):
        resp = client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 401


@pytest.mark.api
class TestForgotPassword:
    def test_forgot_password_registered_email(self, client):
        client.post("/api/v1/auth/register", json={
            "email": "forgot@example.com",
            "username": "forgotuser",
            "full_name": "Forgot User",
            "password": "ForgotPass1!",
        })
        resp = client.post("/api/v1/auth/forgot-password", json={
            "email": "forgot@example.com",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["reset_token"] != ""
        assert data["expires_in_minutes"] > 0

    def test_forgot_password_unknown_email(self, client):
        resp = client.post("/api/v1/auth/forgot-password", json={
            "email": "unknown@example.com",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["reset_token"] == ""
