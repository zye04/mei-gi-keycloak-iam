from fastapi.testclient import TestClient
from main import app
from auth import require_role
from fastapi import Depends, FastAPI, Request
from unittest.mock import MagicMock
import pytest

client = TestClient(app)

def test_index():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "app": "RetailCorp Portal"}

def test_admin_no_session():
    # Should return 401 if no user in session
    response = client.get("/admin")
    assert response.status_code == 401
    assert "Sessão expirada" in response.json()["detail"]

def test_require_role_logic():
    # Test the role_checker directly with various cases
    checker = require_role("admin")
    
    # Case 1: No user
    mock_request = MagicMock()
    mock_request.session = {}
    mock_request.url.path = "/admin"
    mock_request.client.host = "127.0.0.1"
    
    with pytest.raises(Exception) as excinfo:
        checker(mock_request)
    assert excinfo.value.status_code == 401
    assert "Sessão expirada" in excinfo.value.detail
    
    # Case 2: Wrong role
    mock_request.session = {"user": {
        "preferred_username": "testuser",
        "realm_access": {"roles": ["cashier"]}
    }}
    with pytest.raises(Exception) as excinfo:
        checker(mock_request)
    assert excinfo.value.status_code == 403
    assert "Permissões insuficientes" in excinfo.value.detail
    assert "admin" in excinfo.value.detail
    
    # Case 3: Correct role
    mock_request.session = {"user": {
        "preferred_username": "adminuser",
        "realm_access": {"roles": ["admin", "default-roles"]}
    }}
    user = checker(mock_request)
    assert user["preferred_username"] == "adminuser"

    # Case 4: Multiple roles allowed
    checker_multi = require_role("admin", "hr")
    mock_request.session = {"user": {
        "preferred_username": "hruser",
        "realm_access": {"roles": ["hr"]}
    }}
    user = checker_multi(mock_request)
    assert user["preferred_username"] == "hruser"

def test_require_role_edge_cases():
    checker = require_role("admin")
    mock_request = MagicMock()
    mock_request.url.path = "/test"
    mock_request.client.host = "127.0.0.1"

    # Edge Case: realm_access missing
    mock_request.session = {"user": {"preferred_username": "user1"}}
    with pytest.raises(Exception) as excinfo:
        checker(mock_request)
    assert excinfo.value.status_code == 403

    # Edge Case: roles not a list
    mock_request.session = {"user": {
        "preferred_username": "user1",
        "realm_access": {"roles": "not-a-list"}
    }}
    with pytest.raises(Exception) as excinfo:
        checker(mock_request)
    assert excinfo.value.status_code == 403

    # Edge Case: realm_access not a dict
    mock_request.session = {"user": {
        "preferred_username": "user1",
        "realm_access": "not-a-dict"
    }}
    with pytest.raises(Exception) as excinfo:
        checker(mock_request)
    assert excinfo.value.status_code == 403
