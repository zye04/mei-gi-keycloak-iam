from authlib.integrations.starlette_client import OAuth
from config import settings

oauth = OAuth()

oauth.register(
    name="keycloak",
    client_id=settings.keycloak_client_id,
    client_secret=settings.keycloak_client_secret,
    authorize_url=(
        f"{settings.keycloak_public_url}/realms/{settings.keycloak_realm}"
        "/protocol/openid-connect/auth"
    ),
    access_token_url=(
        f"{settings.keycloak_internal_url}/realms/{settings.keycloak_realm}"
        "/protocol/openid-connect/token"
    ),
    jwks_uri=(
        f"{settings.keycloak_internal_url}/realms/{settings.keycloak_realm}"
        "/protocol/openid-connect/certs"
    ),
    userinfo_endpoint=(
        f"{settings.keycloak_internal_url}/realms/{settings.keycloak_realm}"
        "/protocol/openid-connect/userinfo"
    ),
    client_kwargs={
        "scope": "openid email profile roles",
        "token_endpoint_auth_method": "client_secret_post",
    },
)