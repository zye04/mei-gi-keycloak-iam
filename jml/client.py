import os
import sys
import secrets
import string
import re
from dotenv import load_dotenv
from keycloak import KeycloakAdmin

# Tenta carregar o .env da raiz do projeto
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path)

class KeycloakClient:
    """
    Wrapper para a API Admin do Keycloak.
    Centraliza a configuração e garante que as variáveis JML têm prioridade.
    """

    # Configurações de segurança e negócio
    MFA_REQUIRED_ROLES = ["admin", "hr", "store_manager"]
    ALLOWED_EMAIL_DOMAIN = "retailcorp.local"
    PASSWORD_LENGTH = 16
    
    # Política de Transições Permitidas (Issue 16)
    # Define para quais roles um determinado role pode evoluir/mudar
    ROLE_TRANSITIONS = {
        "cashier": ["store_manager", "warehouse", "hr"],
        "warehouse": ["store_manager", "cashier"],
        "store_manager": ["admin", "hr", "warehouse"],
        "hr": ["admin", "store_manager"],
        "supplier": ["supplier"], # Fornecedores são isolados
        "admin": ["hr", "store_manager", "cashier", "warehouse"]
    }
    
    def __init__(self):
        # Prioridade para variáveis JML_*, fallback para as gerais
        self.server_url = os.getenv("JML_KEYCLOAK_URL", os.getenv("KEYCLOAK_PUBLIC_URL", "http://localhost:8080"))
        self.username = os.getenv("JML_ADMIN_USER", os.getenv("KEYCLOAK_ADMIN"))
        self.password = os.getenv("JML_ADMIN_PASSWORD", os.getenv("KEYCLOAK_ADMIN_PASSWORD"))
        self.realm_name = os.getenv("JML_REALM", os.getenv("KEYCLOAK_REALM", "retailcorp"))

        self._validate_config()
        self._admin = None

    def _validate_config(self):
        missing = []
        if not self.server_url: missing.append("JML_KEYCLOAK_URL")
        if not self.username: missing.append("JML_ADMIN_USER")
        if not self.password: missing.append("JML_ADMIN_PASSWORD")
        
        if missing:
            print(f"[ERROR] Variáveis de ambiente em falta no .env: {', '.join(missing)}")
            sys.exit(1)

    @property
    def admin(self) -> KeycloakAdmin:
        """Retorna a instância do KeycloakAdmin (lazy loading)."""
        if self._admin is None:
            try:
                self._admin = KeycloakAdmin(
                    server_url=self.server_url,
                    username=self.username,
                    password=self.password,
                    realm_name=self.realm_name,
                    user_realm_name="master",
                    verify=True
                )
            except Exception as e:
                print(f"[ERROR] Não foi possível ligar à API Admin do Keycloak: {e}")
                sys.exit(1)
        return self._admin

    def get_user_id(self, username: str) -> str:
        """Resolve username para ID e sai com erro se não encontrar."""
        user_id = self.admin.get_user_id(username)
        if not user_id:
            print(f"[ERROR] Utilizador '{username}' não encontrado no Keycloak.")
            sys.exit(1)
        return user_id

    def get_role(self, role_name: str, required: bool = True):
        """Obtém a representação do role e valida se existe."""
        try:
            return self.admin.get_realm_role(role_name)
        except Exception:
            if required:
                print(f"[ERROR] Role '{role_name}' não encontrado no Keycloak.")
                sys.exit(1)
            return None

    @staticmethod
    def generate_random_password(length: int = 16) -> str:
        """Gera uma password aleatória forte (letras, números e símbolos)."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            password = ''.join(secrets.choice(alphabet) for _ in range(length))
            # Garantir pelo menos um de cada tipo para passar em políticas comuns
            if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)):
                return password

    def validate_email(self, email: str) -> bool:
        """Valida se o email segue o formato correto e o domínio corporativo."""
        pattern = rf"^[a-zA-Z0-9._%+-]+@{re.escape(self.ALLOWED_EMAIL_DOMAIN)}$"
        return bool(re.match(pattern, email))

def get_admin_client():
    """Função utilitária para os scripts JML."""
    return KeycloakClient().admin

def get_client():
    """Retorna a instância do wrapper KeycloakClient."""
    return KeycloakClient()
