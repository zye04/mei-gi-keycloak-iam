import os
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO

import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from client import get_client
from leaver import process_leaver

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

class TestIntegrationLeaver(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = get_client()
        cls.admin = cls.client.admin
        cls.username = "test.leaver.e2e"
        
        # Cleanup
        try:
            uid = cls.admin.get_user_id(cls.username)
            if uid: cls.admin.delete_user(uid)
        except: pass
        
        # Criar user fully set up para permitir login antes do leaver
        cls.admin.create_user({
            "username": cls.username,
            "enabled": True,
            "email": "test.leaver@retailcorp.local",
            "firstName": "Test",
            "lastName": "Leaver",
            "emailVerified": True,
            "requiredActions": []
        })
        cls.user_id = cls.admin.get_user_id(cls.username)
        cls.password = "TempPassword123!"
        cls.admin.set_user_password(cls.user_id, cls.password, temporary=False)
        cls.admin.update_user(cls.user_id, {"requiredActions": []})

    def test_leaver_flow_complete(self):
        """Leaver E2E: sessão ativa antes, conta desativada e login bloqueado depois."""

        # 1) Login antes do leaver
        status_before, payload_before = request_password_grant(self.username, self.password)
        self.assertEqual(status_before, 200, f"Login inicial deveria funcionar: {payload_before}")

        # 2) Sessão ativa confirmada
        sessions_before = self.client.get_user_sessions(self.user_id)
        self.assertGreater(len(sessions_before), 0, "Sessão ativa não foi encontrada no Keycloak")

        # 3) Conta enabled antes
        user_before = self.admin.get_user(self.user_id)
        self.assertTrue(user_before.get("enabled"), "Utilizador deveria estar enabled")

        # 4) Executar leaver
        with redirect_stdout(StringIO()):
            process_leaver(self.username, confirm=True, client=self.client)

        # 5) Conta desativada
        user_after = self.admin.get_user(self.user_id)
        self.assertFalse(user_after.get("enabled"), "Utilizador não foi desativado")

        # 6) Sessões revogadas
        sessions_after = self.client.get_user_sessions(self.user_id)
        self.assertEqual(len(sessions_after), 0, "Sessões não foram revogadas")

        # 7) Login bloqueado após leaver
        status_after, payload_after = request_password_grant(self.username, self.password)
        self.assertNotEqual(status_after, 200, "Login deveria falhar após leaver")
        self.assertEqual(payload_after.get("error"), "invalid_grant")

        print(f"[E2E] Leaver '{self.username}' validado: conta desativada, login bloqueado.")

if __name__ == '__main__':
    unittest.main()
