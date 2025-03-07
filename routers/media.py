from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from typing import List
import shutil
import os
import time
from database import get_db
from .auth import get_current_user
from models import User, MediaFile

router = APIRouter()

# Configure media settings
BASE_DIR = Path(__file__).resolve().parent.parent
MEDIA_DIR = BASE_DIR / "static" / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file types
ALLOWED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_AUDIO_TYPES = {".mp3", ".wav", ".ogg", ".m4a"}
ALLOWED_VIDEO_TYPES = {".mp4", ".webm", ".ogg"}
ALLOWED_EXTENSIONS = ALLOWED_IMAGE_TYPES | ALLOWED_AUDIO_TYPES | ALLOWED_VIDEO_TYPES

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate file size
    file_size = 0
    chunk_size = 1024
    chunks = []
    
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        file_size += len(chunk)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum limit of {MAX_FILE_SIZE // (1024 * 1024)}MB"
            )
        chunks.append(chunk)
    
    # Reset file position
    await file.seek(0)
    
    # Validate file type
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Generate unique filename
    timestamp = int(time.time())
    unique_filename = f"{timestamp}_{file.filename}"
    file_path = MEDIA_DIR / unique_filename
    
    # Save file
    try:
        with file_path.open("wb") as f:
            for chunk in chunks:
                f.write(chunk)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Create MediaFile record
    media_file = MediaFile(
        filename=file.filename,
        file_path=f"/static/media/{unique_filename}",
        file_type=file_ext.lstrip('.'),
        uploader_id=current_user.id
    )
    db.add(media_file)
    await db.commit()
    await db.refresh(media_file)
    
    # Return file information
    return {
        "id": media_file.id,
        "url": media_file.file_path,
        "filename": media_file.filename,
        "file_type": media_file.file_type
    }

@router.get("/files")
async def list_media_files(
    current_user: User = Depends(get_current_user)
) -> List[str]:
    files = [f for f in MEDIA_DIR.iterdir() if f.is_file()]
    return [f"/static/media/{f.name}" for f in files]

@router.post("/attach/{article_id}")
async def attach_media_to_article(
    article_id: int,
    media_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get the article and media file
    article = await db.get(Article, article_id)
    media_file = await db.get(MediaFile, media_id)
    
    if not article or not media_file:
        raise HTTPException(status_code=404, detail="Article or media file not found")
    
    # Check if user owns the article
    if article.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this article")
    
    # Add media file to article
    article.media_files.append(media_file)
    await db.commit()
    
    return {"message": "Media file attached successfully"}