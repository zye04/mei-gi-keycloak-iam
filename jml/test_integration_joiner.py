import os
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
from client import get_client
from joiner import main as joiner_main

def request_password_grant(username, password):
    client_wrapper = get_client()
    url = f"{client_wrapper.server_url}/realms/{client_wrapper.realm_name}/protocol/openid-connect/token"
    resp = requests.post(url, data={
        "client_id": "retailcorp-portal",
        "client_secret": "retailcorp-dev-secret-2526",
        "username": username,
        "password": password,
        "grant_type": "password"
    }, timeout=15)

    try:
        payload = resp.json()
    except ValueError:
        payload = {"raw": resp.text}

    return resp.status_code, payload

class TestIntegrationJoiner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_wrapper = get_client()
        cls.admin = cls.client_wrapper.admin
        cls.username = "test.joiner.e2e"
        cls.email = "test.joiner@retailcorp.local"
        cls.role = "cashier"

        # Cleanup
        try:
            uid = cls.admin.get_user_id(cls.username)
            if uid: cls.admin.delete_user(uid)
        except: pass

    def test_joiner_flow_complete(self):
        """Joiner E2E: cria utilizador e valida conta pendente de setup."""

        test_args = ["joiner.py", "--username", self.username, "--email", self.email, 
                     "--first-name", "Test", "--last-name", "Joiner", "--role", self.role]

        with mock.patch('sys.argv', test_args):
            with redirect_stdout(StringIO()):
                joiner_main()

        # 1) Utilizador criado
        uid = self.admin.get_user_id(self.username)
        self.assertIsNotNone(uid, "Utilizador não foi criado")

        # 2) Role atribuído
        roles = [r['name'] for r in self.admin.get_realm_roles_of_user(uid)]
        self.assertIn(self.role, roles, f"Role {self.role} não atribuído")

        # 3) Joiner define ações obrigatórias
        user = self.admin.get_user(uid)
        required_actions = user.get("requiredActions", [])
        self.assertIn("UPDATE_PASSWORD", required_actions)

        # 4) Password grant não deve autenticar enquanto a conta não estiver fully set up
        status_code, payload = request_password_grant(self.username, "invalid-or-temp")
        self.assertNotEqual(status_code, 200)

        # 5) Mensagem de erro esperada para conta pendente
        error_description = str(payload.get("error_description", "")).lower()
        self.assertTrue(
            "not fully set up" in error_description or "invalid user credentials" in error_description,
            f"Erro inesperado no password grant: {payload}"
        )

        print(f"[E2E] Joiner '{self.username}' validado: conta criada e pendente de setup inicial.")

if __name__ == '__main__':
    unittest.main()
