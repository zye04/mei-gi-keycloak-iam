import unittest
from unittest.mock import MagicMock, patch
from mover import process_mover, MoverError

class TestMover(unittest.TestCase):

    def setUp(self):
        # Mock do cliente e da admin do Keycloak
        self.mock_client = MagicMock()
        self.mock_admin = self.mock_client.admin
        
        # Configuração padrão de roles para a política (deve bater com client.py)
        self.mock_client.ROLE_TRANSITIONS = {
            "cashier": ["store_manager"],
            "supplier": ["supplier"]
        }
        self.mock_client.MFA_REQUIRED_ROLES = ["store_manager"]
        self.mock_client.get_user_id.return_value = "user-123"
        self.mock_client.get_role.side_effect = lambda name, required: {"name": name}

    def test_transition_forbidden(self):
        """Valida que transições não permitidas lançam erro."""
        with self.assertRaises(MoverError) as cm:
            process_mover("test.user", "supplier", "admin", client=self.mock_client)
        self.assertIn("Transição proibida", str(cm.exception))

    def test_transition_allowed_with_mfa(self):
        """Valida transição permitida e ativação de MFA."""
        self.mock_admin.get_user.return_value = {"enabled": True, "requiredActions": []}
        self.mock_admin.get_realm_roles_of_user.side_effect = [
            [{"name": "cashier"}], # Antes
            [{"name": "store_manager"}] # Depois
        ]

        result = process_mover("test.user", "cashier", "store_manager", client=self.mock_client)
        
        self.assertTrue(result)
        # Verifica se atribuiu o novo e removeu o antigo
        self.mock_admin.assign_realm_roles.assert_called()
        self.mock_admin.delete_realm_roles_of_user.assert_called()
        # Verifica se forçou MFA
        self.mock_admin.update_user.assert_called_with("user-123", {"requiredActions": ["CONFIGURE_TOTP"]})

    def test_user_disabled_error(self):
        """Valida que utilizadores desativados não podem ser movidos."""
        self.mock_admin.get_user.return_value = {"enabled": False}
        
        with self.assertRaises(MoverError) as cm:
            process_mover("test.user", "cashier", "store_manager", client=self.mock_client)
        self.assertIn("está desativado", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
