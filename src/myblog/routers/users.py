from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from myblog.database import get_db
from myblog.models import User, Role
from .auth import get_current_user
from fastapi.templating import Jinja2Templates
from pathlib import Path
import markdown
from fastapi.responses import RedirectResponse

router = APIRouter()

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))# Dependency to get current user


@router.put("/{user_id}/role")
async def set_user_role(
    user_id: int,
    role: Role = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if the current user is an admin
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to set user roles")

    # Fetch the user to update
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update the user's role
    user.role = role
    await db.commit()
    await db.refresh(user)

    return {"message": "User role updated successfully", "user_id": user.id, "new_role": user.role}

@router.get("/")
async def role_page(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if the current user is an admin
    if current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this page")

    # Fetch all users
    query = select(User)
    result = await db.execute(query)
    users = result.scalars().all()

    return templates.TemplateResponse(
        "users/role.html",
        {"request": request, "users": users}
    )