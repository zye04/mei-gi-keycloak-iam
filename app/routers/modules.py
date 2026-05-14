from fastapi import APIRouter, Depends

from auth import require_role

router = APIRouter(tags=["Modules"])


@router.get("/admin")
async def admin_panel(user: dict = Depends(require_role("admin"))):
    return {"message": "Welcome, Administrator", "user": user["preferred_username"]}


@router.get("/pos")
async def pos_module(user: dict = Depends(require_role("admin", "store_manager", "cashier"))):
    return {"module": "Point of Sale", "user": user["preferred_username"]}


@router.get("/inventory")
async def inventory_module(user: dict = Depends(require_role("admin", "store_manager", "warehouse"))):
    return {"module": "Inventory Management", "user": user["preferred_username"]}


@router.get("/reports")
async def reports_module(user: dict = Depends(require_role("admin", "store_manager"))):
    return {"module": "Financial Reports", "user": user["preferred_username"]}


@router.get("/suppliers")
async def suppliers_module(user: dict = Depends(require_role("admin", "supplier"))):
    return {"module": "B2B Supplier Portal", "user": user["preferred_username"]}


@router.get("/hr")
async def hr_module(user: dict = Depends(require_role("admin", "hr"))):
    return {"module": "HR Management & JML", "user": user["preferred_username"]}
