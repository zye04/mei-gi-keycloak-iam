import os
import sys
import unittest

import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from client import get_client
from mover import process_mover, MoverError

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

class TestIntegrationMover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = get_client()
        cls.admin = cls.client.admin
        cls.test_user = "test.mover.e2e"
        
        # Cleanup
        try:
            uid = cls.admin.get_user_id(cls.test_user)
            if uid: cls.admin.delete_user(uid)
        except: pass
        
        # Criar user fully set up para permitir password grant antes da promoção
        cls.admin.create_user({
            "username": cls.test_user,
            "enabled": True,
            "email": "test.mover@retailcorp.local",
            "firstName": "Test",
            "lastName": "Mover",
            "emailVerified": True,
            "requiredActions": []
        })
        cls.user_id = cls.admin.get_user_id(cls.test_user)
        cls.password = "TempPassword123!"
        cls.admin.set_user_password(cls.user_id, cls.password, temporary=False)
        cls.admin.update_user(cls.user_id, {"requiredActions": []})

    def test_mover_with_session_revocation(self):
        """Mover E2E: sessão ativa antes, revogada depois e MFA exigido."""

        # Setup: role inicial
        cashier_role = self.admin.get_realm_role("cashier")
        self.admin.assign_realm_roles(self.user_id, [cashier_role])

        # 1) Login antes do mover (conta fully set up)
        status_before, payload_before = request_password_grant(self.test_user, self.password)
        self.assertEqual(status_before, 200, f"Password grant deveria funcionar antes do mover: {payload_before}")

        # 2) Sessão ativa antes da mudança
        sessions_before = self.client.get_user_sessions(self.user_id)
        self.assertGreater(len(sessions_before), 0, "Sessão ativa não encontrada antes do mover")

        # 3) Executar mover
        result = process_mover(self.test_user, "cashier", "store_manager", client=self.client)
        self.assertTrue(result, "Mover falhou")

        # 4) Roles finais corretos
        final_roles = [r['name'] for r in self.admin.get_realm_roles_of_user(self.user_id)]
        self.assertIn("store_manager", final_roles)
        self.assertNotIn("cashier", final_roles)

        # 5) MFA exigido para role sensível
        user_info = self.admin.get_user(self.user_id)
        self.assertIn("CONFIGURE_TOTP", user_info.get("requiredActions", []))

        # 6) Sessões revogadas pelo mover
        sessions_after = self.client.get_user_sessions(self.user_id)
        self.assertEqual(len(sessions_after), 0, "Sessões não foram revogadas após mover")

        print(f"[E2E] Mover '{self.test_user}' validado: sessão revogada, MFA exigido.")

if __name__ == '__main__':
    unittest.main()
