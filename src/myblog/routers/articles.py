from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
from myblog.database import get_db
from myblog.models import Article, User
from .auth import get_current_user
from fastapi.templating import Jinja2Templates
from pathlib import Path
import markdown
from fastapi.responses import RedirectResponse

router = APIRouter()

# Setup templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Article schemas
from pydantic import BaseModel
from datetime import datetime

class ArticleCreate(BaseModel):
    title: str
    content: str

class ArticleResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: datetime
    updated_at: datetime
    author_id: int

    class Config:
        from_attributes = True

# Article endpoints
@router.get("/", response_model=List[ArticleResponse])
async def list_articles(request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Article).order_by(Article.created_at.desc()).options(selectinload(Article.author))
    result = await db.execute(query)
    articles = result.scalars().all()
    
    # Convert Markdown content to HTML
    for article in articles:
        article.content = markdown.markdown(article.content)
    
    return templates.TemplateResponse(
        "articles/list.html",
        {"request": request, "articles": articles, "current_user": current_user}
    )

@router.get("/new", response_model=None)
async def new_article_form(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse(
        "articles/editor.html",
        {"request": request, "title": "New Article", "current_user": current_user}
    )

@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: int, request: Request, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = select(Article).where(Article.id == article_id).options(selectinload(Article.author))
    result = await db.execute(query)
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # Convert Markdown content to HTML
    article.content = markdown.markdown(article.content)
    
    return templates.TemplateResponse(
        "articles/detail.html",
        {"request": request, "article": article, "current_user": current_user}
    )

@router.post("/", response_model=ArticleResponse)
async def create_article(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    form_data = await request.form()
    new_article = Article(
        title=form_data.get('title'),
        content=form_data.get('content'),
        author_id=current_user.id
    )
    db.add(new_article)
    await db.commit()
    await db.refresh(new_article)
    return RedirectResponse(url="/articles", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/{article_id}/edit", response_model=None)
async def edit_article_form(
    article_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Article).where(Article.id == article_id)
    result = await db.execute(query)
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if article.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this article")
    
    return templates.TemplateResponse(
        "articles/editor.html",
        {"request": request, "article": article, "title": "Edit Article"}
    )

@router.put("/{article_id}", response_model=ArticleResponse)
@router.post("/{article_id}", response_model=ArticleResponse)
async def update_article(
    article_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    form_data = await request.form()
    query = select(Article).where(Article.id == article_id)
    result = await db.execute(query)
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if article.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this article")
    
    article.title = form_data.get('title')
    article.content = form_data.get('content')
    await db.commit()
    await db.refresh(article)
    return RedirectResponse(url="/articles", status_code=status.HTTP_303_SEE_OTHER)

@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Article).where(Article.id == article_id)
    result = await db.execute(query)
    article = result.scalar_one_or_none()
    
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    if article.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this article")
    
    await db.delete(article)
    await db.commit()
    return None