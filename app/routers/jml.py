import sys
import os

# Resolve o caminho para os scripts JML:
#   - dentro do container Docker: /jml (copiado pelo Dockerfile)
#   - desenvolvimento local: ../../jml relativo a este ficheiro
_jml_dir = "/jml" if os.path.isdir("/jml") else os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "jml")
)
sys.path.insert(0, _jml_dir)

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from auth import require_role
from client import ClientError
from joiner import JoinerError, process_joiner
from leaver import LeaverError, process_leaver
from mover import MoverError, process_mover

router = APIRouter(prefix="/jml", tags=["JML"])
templates = Jinja2Templates(directory="templates")

# Guardado como variável de módulo para permitir dependency_overrides nos testes
_jml_auth = require_role("admin", "hr")


@router.get("")
async def jml_panel(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    roles = user.get("realm_access", {}).get("roles", [])
    if not any(r in roles for r in ["admin", "hr"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso restrito a admin e hr")
    return templates.TemplateResponse("jml.html", {"request": request, "user": user})

RoleLiteral = Literal["admin", "hr", "store_manager", "cashier", "warehouse", "supplier"]


class JoinerRequest(BaseModel):
    username: str
    email: str
    first_name: str
    last_name: str
    role: RoleLiteral


class MoverRequest(BaseModel):
    username: str
    from_role: str
    to_role: str


class LeaverRequest(BaseModel):
    username: str
    dry_run: bool = False


@router.post("/joiner", status_code=status.HTTP_201_CREATED)
def joiner_endpoint(body: JoinerRequest, user: dict = Depends(_jml_auth)):
    try:
        result = process_joiner(body.username, body.email, body.first_name, body.last_name, body.role)
        return {
            "status": "created",
            "username": result["username"],
            "role": result["role"],
            "required_actions": result["required_actions"],
            "temp_password": result["temp_password"],
        }
    except (JoinerError, ClientError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/mover")
def mover_endpoint(body: MoverRequest, user: dict = Depends(_jml_auth)):
    try:
        process_mover(body.username, body.from_role, body.to_role)
        return {"status": "moved", "username": body.username, "from_role": body.from_role, "to_role": body.to_role}
    except (MoverError, ClientError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/leaver")
def leaver_endpoint(body: LeaverRequest, user: dict = Depends(_jml_auth)):
    try:
        process_leaver(body.username, confirm=True, dry_run=body.dry_run)
        return {"status": "dry_run" if body.dry_run else "offboarded", "username": body.username}
    except (LeaverError, ClientError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
