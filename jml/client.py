import os
import sys
import secrets
import string
import re
from dotenv import load_dotenv
from keycloak import KeycloakAdmin

dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path=dotenv_path)


class ClientError(Exception):
    """Erro de configuração ou comunicação com o Keycloak — seguro para propagar em FastAPI."""
    pass


class KeycloakClient:
    MFA_REQUIRED_ROLES = ["admin", "hr", "store_manager"]
    ALLOWED_EMAIL_DOMAIN = "retailcorp.local"
    PASSWORD_LENGTH = 16

    ROLE_TRANSITIONS = {
        "cashier": ["store_manager", "warehouse", "hr"],
        "warehouse": ["store_manager", "cashier"],
        "store_manager": ["admin", "hr", "warehouse"],
        "hr": ["admin", "store_manager"],
        "supplier": ["supplier"],
        "admin": ["hr", "store_manager", "cashier", "warehouse"],
    }

    def __init__(self):
        # Fallback chain: JML_KEYCLOAK_URL → KEYCLOAK_INTERNAL_URL (Docker) → KEYCLOAK_PUBLIC_URL (host)
        self.server_url = os.getenv(
            "JML_KEYCLOAK_URL",
            os.getenv("KEYCLOAK_INTERNAL_URL", os.getenv("KEYCLOAK_PUBLIC_URL", "http://localhost:8080")),
        )
        self.username = os.getenv("JML_ADMIN_USER", os.getenv("KEYCLOAK_ADMIN"))
        self.password = os.getenv("JML_ADMIN_PASSWORD", os.getenv("KEYCLOAK_ADMIN_PASSWORD"))
        self.realm_name = os.getenv("JML_REALM", os.getenv("KEYCLOAK_REALM", "retailcorp"))
        self._validate_config()
        self._admin = None

    def _validate_config(self):
        missing = []
        if not self.server_url:
            missing.append("JML_KEYCLOAK_URL")
        if not self.username:
            missing.append("JML_ADMIN_USER")
        if not self.password:
            missing.append("JML_ADMIN_PASSWORD")
        if missing:
            raise ClientError(f"Variáveis de ambiente em falta no .env: {', '.join(missing)}")

    @property
    def admin(self) -> KeycloakAdmin:
        if self._admin is None:
            try:
                self._admin = KeycloakAdmin(
                    server_url=self.server_url,
                    username=self.username,
                    password=self.password,
                    realm_name=self.realm_name,
                    user_realm_name="master",
                    verify=True,
                )
            except Exception as e:
                raise ClientError(f"Não foi possível ligar à API Admin do Keycloak: {e}")
        return self._admin

    def get_user_id(self, username: str) -> str:
        user_id = self.admin.get_user_id(username)
        if not user_id:
            raise ClientError(f"Utilizador '{username}' não encontrado no Keycloak.")
        return user_id

    def get_user_sessions(self, user_id: str):
        try:
            return self.admin.get_user_sessions(user_id)
        except AttributeError:
            try:
                return self.admin.get_sessions(user_id)
            except Exception:
                pass

            try:
                import requests
                url = f"{self.server_url}/admin/realms/{self.realm_name}/users/{user_id}/sessions"
                token_data = getattr(self.admin.connection, "token", None)
                access_token = None
                if isinstance(token_data, dict):
                    access_token = token_data.get("access_token")
                if not access_token:
                    try:
                        token_data = self.admin.connection.refresh_token()
                        if isinstance(token_data, dict):
                            access_token = token_data.get("access_token")
                    except Exception:
                        access_token = None
                if not access_token:
                    return []
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(url, headers=headers, timeout=10)
                return response.json() if response.status_code == 200 else []
            except Exception:
                return []

    def get_role(self, role_name: str, required: bool = True):
        try:
            return self.admin.get_realm_role(role_name)
        except Exception:
            if required:
                raise ClientError(f"Role '{role_name}' não encontrado no Keycloak.")
            return None

    @staticmethod
    def generate_random_password(length: int = 16) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(length))
            if (
                any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)
                and any(c in "!@#$%^&*" for c in password)
            ):
                return password

    def validate_email(self, email: str) -> bool:
        pattern = rf"^[a-zA-Z0-9._%+-]+@{re.escape(self.ALLOWED_EMAIL_DOMAIN)}$"
        return bool(re.match(pattern, email))


def get_admin_client():
    return KeycloakClient().admin


def get_client():
    return KeycloakClient()
