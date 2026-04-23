import logging
from fastapi import Request, HTTPException, status
from authlib.integrations.starlette_client import OAuth
from config import settings

# Configure basic logging for auditing (Phase 4 precursor)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("auth_audit")

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

def require_role(*required_roles: str):
    """
    FastAPI dependency that checks if the user in session has at least one of the required roles.

    Args:
        *required_roles: List of roles allowed to access the resource.

    Returns:
        dict: The user info if authorized.

    Raises:
        HTTPException: 401 if unauthenticated, 403 if unauthorized.
    """
    def role_checker(request: Request):
        user = request.session.get("user")
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        if not user:
            logger.warning(f"Access Denied: Unauthenticated attempt to {path} from IP {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sessão expirada ou não autenticada. Por favor, faça login."
            )

        username = user.get("preferred_username", "unknown_user")

        # Safe extraction of roles with edge case handling
        realm_access = user.get("realm_access", {})
        if not isinstance(realm_access, dict):
            realm_access = {}
        user_roles = realm_access.get("roles", [])

        if not isinstance(user_roles, list):
            user_roles = []

        # Check if at least one of the required_roles is in user_roles
        has_access = any(role in user_roles for role in required_roles)

        if not has_access:
            logger.error(
                f"Access Denied: User '{username}' (Roles: {user_roles}) "
                f"tried to access {path} without required roles: {required_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permissões insuficientes. Requer um dos roles: {list(required_roles)}"
            )

        logger.info(f"Access Granted: User '{username}' accessed {path}")
        return user
    return role_checker