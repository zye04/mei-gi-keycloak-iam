"""
Testes de integração HTTP para os endpoints JML.

Cada teste passa pelo HTTP → autenticação/autorização → lógica JML.
As funções process_* são mockadas para não depender do Keycloak a correr.
Para testes E2E com Keycloak real, levantar o docker-compose e testar manualmente.
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from routers.jml import _jml_auth

FAKE_ADMIN = {"preferred_username": "admin.test", "realm_access": {"roles": ["admin"]}}

client = TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def as_admin():
    """Injeta um utilizador admin na dependência de autenticação."""
    app.dependency_overrides[_jml_auth] = lambda: FAKE_ADMIN
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Joiner
# ---------------------------------------------------------------------------

def test_joiner_cria_utilizador_cashier(as_admin):
    with patch("routers.jml.process_joiner") as mock:
        mock.return_value = {
            "user_id": "uuid-1",
            "username": "ana.silva",
            "role": "cashier",
            "temp_password": "Secret1!",
            "required_actions": ["UPDATE_PASSWORD"],
        }
        resp = client.post("/jml/joiner", json={
            "username": "ana.silva",
            "email": "ana.silva@retailcorp.local",
            "first_name": "Ana",
            "last_name": "Silva",
            "role": "cashier",
        })

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "created"
    assert data["username"] == "ana.silva"
    assert data["role"] == "cashier"
    assert "UPDATE_PASSWORD" in data["required_actions"]
    assert "CONFIGURE_TOTP" not in data["required_actions"]


def test_joiner_exige_totp_para_role_sensivel(as_admin):
    with patch("routers.jml.process_joiner") as mock:
        mock.return_value = {
            "user_id": "uuid-2",
            "username": "rui.manager",
            "role": "store_manager",
            "temp_password": "Secret1!",
            "required_actions": ["UPDATE_PASSWORD", "CONFIGURE_TOTP"],
        }
        resp = client.post("/jml/joiner", json={
            "username": "rui.manager",
            "email": "rui.manager@retailcorp.local",
            "first_name": "Rui",
            "last_name": "Manager",
            "role": "store_manager",
        })

    assert resp.status_code == 201
    assert "CONFIGURE_TOTP" in resp.json()["required_actions"]


def test_joiner_devolve_400_em_erro(as_admin):
    from joiner import JoinerError
    with patch("routers.jml.process_joiner", side_effect=JoinerError("Utilizador já existe")):
        resp = client.post("/jml/joiner", json={
            "username": "dup",
            "email": "dup@retailcorp.local",
            "first_name": "X",
            "last_name": "X",
            "role": "cashier",
        })

    assert resp.status_code == 400
    assert "Utilizador já existe" in resp.json()["detail"]


def test_joiner_rejeita_sem_sessao():
    """Sem sessão autenticada deve receber 401."""
    resp = client.post("/jml/joiner", json={
        "username": "x",
        "email": "x@retailcorp.local",
        "first_name": "X",
        "last_name": "X",
        "role": "cashier",
    })
    assert resp.status_code == 401


def test_joiner_rejeita_role_errado():
    """Utilizador com role insuficiente recebe 403.

    dependency_overrides substitui toda a dependência — para simular um 403
    o override tem de levantar a exceção como o require_role faria.
    """
    from fastapi import HTTPException

    def cashier_sem_acesso():
        raise HTTPException(status_code=403, detail="Permissões insuficientes.")

    app.dependency_overrides[_jml_auth] = cashier_sem_acesso
    try:
        resp = client.post("/jml/joiner", json={
            "username": "qualquer",
            "email": "qualquer@retailcorp.local",
            "first_name": "X",
            "last_name": "X",
            "role": "cashier",
        })
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Mover
# ---------------------------------------------------------------------------

def test_mover_transicao_valida(as_admin):
    with patch("routers.jml.process_mover") as mock:
        mock.return_value = True
        resp = client.post("/jml/mover", json={
            "username": "joao.func",
            "from_role": "cashier",
            "to_role": "store_manager",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "moved"
    assert data["from_role"] == "cashier"
    assert data["to_role"] == "store_manager"


def test_mover_transicao_proibida_devolve_400(as_admin):
    from mover import MoverError
    with patch("routers.jml.process_mover", side_effect=MoverError("Transição proibida pela política: cashier -> supplier")):
        resp = client.post("/jml/mover", json={
            "username": "joao.func",
            "from_role": "cashier",
            "to_role": "supplier",
        })

    assert resp.status_code == 400
    assert "Transição proibida" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Leaver
# ---------------------------------------------------------------------------

def test_leaver_offboarding_real(as_admin):
    with patch("routers.jml.process_leaver") as mock:
        mock.return_value = True
        resp = client.post("/jml/leaver", json={"username": "ex.func"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "offboarded"
    mock.assert_called_once_with("ex.func", confirm=True, dry_run=False)


def test_leaver_dry_run(as_admin):
    with patch("routers.jml.process_leaver") as mock:
        mock.return_value = True
        resp = client.post("/jml/leaver", json={"username": "ex.func", "dry_run": True})

    assert resp.status_code == 200
    assert resp.json()["status"] == "dry_run"
    mock.assert_called_once_with("ex.func", confirm=True, dry_run=True)


def test_leaver_utilizador_inexistente_devolve_400(as_admin):
    from leaver import LeaverError
    with patch("routers.jml.process_leaver", side_effect=LeaverError("Utilizador não encontrado")):
        resp = client.post("/jml/leaver", json={"username": "fantasma"})

    assert resp.status_code == 400
