from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from config import settings
from auth import oauth  # noqa: F401 — registo do cliente OIDC
from routers.auth import router as auth_router
from routers.modules import router as modules_router
from routers.jml import router as jml_router

app = FastAPI(title="RetailCorp Portal")

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

app.include_router(auth_router)
app.include_router(modules_router)
app.include_router(jml_router)


@app.get("/")
def index():
    return {"status": "ok", "app": "RetailCorp Portal"}
