from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from myblog.database import get_db
from myblog.models import Card, User
from .auth import get_current_user
from fastapi.templating import Jinja2Templates
from pathlib import Path
import markdown
from fastapi.responses import RedirectResponse

router = APIRouter()

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Card schemas
from pydantic import BaseModel
from datetime import datetime

class CardCreate(BaseModel):
    title: str
    content: str

class CardResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    author_id: int

    class Config:
        from_attributes = True

# Card endpoints
@router.get("/", response_model=List[CardResponse])
async def list_Cards(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Card).order_by(Card.created_at.desc()).options(selectinload(Card.author))
    result = await db.execute(query)
    cards = result.scalars().all()
    
    # Convert Markdown content to HTML
    for card in cards:
        card.content = markdown.markdown(card.content)
    
    return templates.TemplateResponse(
        "cards/list.html",
        {"request": request, "cards": cards, "current_user": current_user}
    )

@router.get("/new", response_model=None)
async def new_card_form(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "cards/editor.html",
        {"request": request, "title": "New Card", "current_user": current_user}
    )

@router.get("/{card_id}", response_model=CardResponse)
async def get_card(card_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Card).where(Card.id == card_id).options(selectinload(Card.author))
    result = await db.execute(query)
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    # Convert Markdown content to HTML
    card.content = markdown.markdown(card.content)
    
    return templates.TemplateResponse(
        "cards/detail.html",
        {"request": request, "card": card, "current_user": current_user}
    )

@router.post("/", response_model=CardResponse)
async def create_card(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    form_data = await request.form()
    new_card = Card(
        title=form_data.get('title'),
        content=form_data.get('content'),
        author_id=current_user.id
    )
    db.add(new_card)
    await db.commit()
    await db.refresh(new_card)
    return RedirectResponse(url="/cards", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/{card_id}/edit", response_model=None)
async def edit_card_form(
    card_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Card).where(Card.id == card_id)
    result = await db.execute(query)
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    if card.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this card")
    
    return templates.TemplateResponse(
        "cards/editor.html",
        {"request": request, "card": card, "title": "Edit Card"}
    )

@router.put("/{card_id}", response_model=CardResponse)
@router.post("/{card_id}", response_model=CardResponse)
async def update_card(
    card_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    form_data = await request.form()
    query = select(Card).where(Card.id == card_id)
    result = await db.execute(query)
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    if card.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this card")
    
    card.title = form_data.get('title')
    card.content = form_data.get('content')
    await db.commit()
    await db.refresh(card)
    return RedirectResponse(url="/cards", status_code=status.HTTP_303_SEE_OTHER)

@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    card_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Card).where(Card.id == card_id)
    result = await db.execute(query)
    card = result.scalar_one_or_none()
    
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    if card.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this card")
    
    await db.delete(card)
    await db.commit()
    return None