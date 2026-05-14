from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import require_role
import audit as audit_module

router = APIRouter(tags=["Audit"])
templates = Jinja2Templates(directory="templates")

_admin_auth = require_role("admin")


@router.get("/admin/audit")
async def audit_panel(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login")
    roles = user.get("realm_access", {}).get("roles", [])
    if "admin" not in roles:
        return RedirectResponse(url="/dashboard")
    events = audit_module.read_events(n=200)
    return templates.TemplateResponse("audit.html", {
        "request": request,
        "user": user,
        "events": events,
    })
