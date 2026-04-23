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

# --- Testes da Matriz de Acesso (Issue 13) ---

@pytest.fixture
def mock_req():
    req = MagicMock()
    req.client.host = "127.0.0.1"
    return req

def test_matrix_admin_access(mock_req):
    """Admin deve ter acesso a tudo."""
    mock_req.session = {"user": {"preferred_username": "admin", "realm_access": {"roles": ["admin"]}}}
    
    # Rotas que o admin deve conseguir aceder
    assert require_role("admin")(mock_req)
    assert require_role("admin", "hr")(mock_req)
    assert require_role("admin", "supplier")(mock_req)

def test_matrix_cashier_access(mock_req):
    """Cashier acede a POS, mas é bloqueado em Admin e Reports."""
    mock_req.session = {"user": {"preferred_username": "caixa1", "realm_access": {"roles": ["cashier"]}}}
    
    # Sucesso: POS (roles: admin, store_manager, cashier)
    assert require_role("admin", "store_manager", "cashier")(mock_req)
    
    # Bloqueio: Admin
    mock_req.url.path = "/admin"
    with pytest.raises(Exception) as exc:
        require_role("admin")(mock_req)
    assert exc.value.status_code == 403

    # Bloqueio: Reports (roles: admin, store_manager)
    mock_req.url.path = "/reports"
    with pytest.raises(Exception) as exc:
        require_role("admin", "store_manager")(mock_req)
    assert exc.value.status_code == 403

def test_matrix_supplier_access(mock_req):
    """Supplier acede a B2B, mas é bloqueado em Inventory."""
    mock_req.session = {"user": {"preferred_username": "fornecedor1", "realm_access": {"roles": ["supplier"]}}}
    
    # Sucesso: Suppliers (roles: admin, supplier)
    assert require_role("admin", "supplier")(mock_req)
    
    # Bloqueio: Inventory (roles: admin, store_manager, warehouse)
    mock_req.url.path = "/inventory"
    with pytest.raises(Exception) as exc:
        require_role("admin", "store_manager", "warehouse")(mock_req)
    assert exc.value.status_code == 403

def test_matrix_hr_access(mock_req):
    """HR acede a HR data, mas é bloqueado em POS."""
    mock_req.session = {"user": {"preferred_username": "rh1", "realm_access": {"roles": ["hr"]}}}
    
    # Sucesso: HR (roles: admin, hr)
    assert require_role("admin", "hr")(mock_req)
    
    # Bloqueio: POS
    mock_req.url.path = "/pos"
    with pytest.raises(Exception) as exc:
        require_role("admin", "store_manager", "cashier")(mock_req)
    assert exc.value.status_code == 403
