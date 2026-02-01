"""Tests for authentication endpoints."""

import pytest
from fastapi import status


class TestRegister:
    """Tests for user registration."""

    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "password": "securepass123",
            "full_name": "New User"
        })
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, client, test_user):
        """Test registration with an existing email fails."""
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "anotherpass123",
            "full_name": "Another User"
        })
        assert response.status_code == status.HTTP_409_CONFLICT


class TestLogin:
    """Tests for user login."""

    def test_login_success(self, client, test_user):
        """Test successful login with valid credentials."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "testpass123"
        })
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, client, test_user):
        """Test login with invalid password fails."""
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetMe:
    """Tests for getting current user info."""

    def test_get_me_authenticated(self, client, auth_headers):
        """Test getting current user info when authenticated."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["full_name"] == "Test User"
        assert data["is_active"] is True

    def test_get_me_unauthenticated(self, client):
        """Test getting current user info without authentication fails."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
