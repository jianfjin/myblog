from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from dotenv import load_dotenv
from myblog.database import init_db
from myblog.routers.auth import get_current_user
from myblog.models import User

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="My Blog")

# Setup CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup database initialization event
@app.on_event("startup")
async def startup_event():
    await init_db()

# Setup static files and templates
BASE_DIR = Path(__file__).resolve().parent / "src" / "myblog"
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Root endpoint
@app.get("/", response_model=None)
async def home(request: Request, current_user: User | None = Depends(get_current_user)):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "Welcome to My Blog", "current_user": current_user}
    )

# Include routers
from myblog.routers import auth, cards

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(cards.router, prefix="/cards", tags=["cards"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)