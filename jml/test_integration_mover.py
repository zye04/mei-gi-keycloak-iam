import unittest
import logging
from client import get_client
from mover import process_mover, MoverError
from keycloak import KeycloakPostError

class TestIntegrationMover(unittest.TestCase):
    """
    Testes de Integração reais contra o Keycloak (Docker).
    AVISO: Requer que o docker-compose esteja UP.
    """

    @classmethod
    def setUpClass(cls):
        cls.client = get_client()
        cls.admin = cls.client.admin
        cls.test_user = "test.mover.integration"
        cls.test_email = "test.mover@retailcorp.local"

        # Garantir que o user não existe antes de começar
        try:
            uid = cls.admin.get_user_id(cls.test_user)
            if uid: cls.admin.delete_user(uid)
        except: pass

        # Criar utilizador base
        cls.admin.create_user({
            "username": cls.test_user,
            "email": cls.test_email,
            "enabled": True,
            "firstName": "Test",
            "lastName": "Integration"
        })
        cls.user_id = cls.admin.get_user_id(cls.test_user)

    @classmethod
    def tearDownClass(cls):
        # Limpeza final
        try:
            cls.admin.delete_user(cls.user_id)
        except: pass

    def test_real_transition_cashier_to_store_manager(self):
        """Valida uma transição real no Keycloak."""
        # 1. Setup: Colocar como cashier
        cashier_role = self.client.get_role("cashier")
        self.admin.assign_realm_roles(self.user_id, [cashier_role])

        # 2. Executar Mover
        result = process_mover(self.test_user, "cashier", "store_manager", client=self.client)
        self.assertTrue(result)

        # 3. Validar estado final
        final_roles = [r['name'] for r in self.admin.get_realm_roles_of_user(self.user_id)]
        self.assertIn("store_manager", final_role_names := final_roles)
        self.assertNotIn("cashier", final_role_names)

        # 4. Validar se MFA foi exigido (Required Actions)
        user_info = self.admin.get_user(self.user_id)
        self.assertIn("CONFIGURE_TOTP", user_info.get("requiredActions", []))

if __name__ == '__main__':
    unittest.main()
