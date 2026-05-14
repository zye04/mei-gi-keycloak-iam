from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import oauth
from config import settings
import audit

router = APIRouter(tags=["Auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login")
async def login(request: Request):
    redirect_uri = f"{settings.app_base_url}/auth/callback"
    return await oauth.keycloak.authorize_redirect(request, redirect_uri)


@router.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.keycloak.authorize_access_token(request)
    user_info = token.get("userinfo")
    request.session["user"] = dict(user_info)
    request.session["access_token"] = token.get("access_token")
    username = user_info.get("preferred_username", "unknown")
    roles = user_info.get("realm_access", {}).get("roles", [])
    ip = request.client.host if request.client else "unknown"
    audit.log_event(audit.LOGIN, username, "/auth/callback", ip, roles=roles)
    return RedirectResponse(url="/dashboard")


@router.get("/logout")
async def logout(request: Request):
    user = request.session.get("user", {})
    username = user.get("preferred_username", "unknown")
    ip = request.client.host if request.client else "unknown"
    audit.log_event(audit.LOGOUT, username, "/logout", ip)
    request.session.clear()
    logout_url = (
        f"{settings.keycloak_public_url}/realms/{settings.keycloak_realm}"
        f"/protocol/openid-connect/logout"
        f"?post_logout_redirect_uri={settings.app_base_url}"
        f"&client_id={settings.keycloak_client_id}"
    )
    return RedirectResponse(url=logout_url)


@router.get("/dashboard")
async def dashboard(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})
