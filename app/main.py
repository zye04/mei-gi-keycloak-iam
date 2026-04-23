from fastapi import FastAPI, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from config import settings
from auth import oauth, require_role

app = FastAPI(title="RetailCorp Portal")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_base_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.app_secret_key,
    https_only=False,
    same_site="lax",
)

@app.get("/")
def index():
    return {"status": "ok", "app": "RetailCorp Portal"}

@app.get("/login")
async def login(request: Request):
    redirect_uri = f"{settings.app_base_url}/auth/callback"
    return await oauth.keycloak.authorize_redirect(request, redirect_uri)

@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.keycloak.authorize_access_token(request)
    user_info = token.get("userinfo")
    request.session["user"] = dict(user_info)
    request.session["access_token"] = token.get("access_token")
    return RedirectResponse(url="/dashboard")

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    logout_url = (
        f"{settings.keycloak_public_url}/realms/{settings.keycloak_realm}"
        f"/protocol/openid-connect/logout"
        f"?post_logout_redirect_uri={settings.app_base_url}"
        f"&client_id={settings.keycloak_client_id}"
    )
    return RedirectResponse(url=logout_url)

@app.get("/dashboard")
async def dashboard(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

@app.get("/admin")
async def admin_panel(user: dict = Depends(require_role("admin"))):
    return {"message": "Welcome, Administrator", "user": user["preferred_username"]}