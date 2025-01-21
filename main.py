from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import string
import random
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
import os
from fastapi.middleware.cors import CORSMiddleware

# Configure SQLAlchemy
DATABASE_URL = "sqlite:///./slugs.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define Slug model
class Slug(Base):
    __tablename__ = "slugs"
    
    slug = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    used = Column(Boolean, default=False)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Montar arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configurar templates
templates = Jinja2Templates(directory="templates")

# Adicionar middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def generate_slug(length=6):
    """Generate a random slug of specified length"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_db():
    """Database session generator"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api")
async def root():
    return {"status": "ok", "message": "API is running"}

@app.get("/generate-slug")
async def generate_new_slug():
    """Generate a new unique slug"""
    db = SessionLocal()
    
    while True:
        new_slug = generate_slug()
        existing_slug = db.query(Slug).filter(Slug.slug == new_slug).first()
        if not existing_slug:
            break
    
    slug_entry = Slug(slug=new_slug)
    db.add(slug_entry)
    db.commit()
    db.close()
    
    return {"slug": new_slug}

@app.get("/validate/{slug}")
async def validate_slug(slug: str):
    """Validate if a slug is valid and not expired"""
    db = SessionLocal()
    slug_entry = db.query(Slug).filter(Slug.slug == slug).first()
    
    if not slug_entry:
        raise HTTPException(status_code=404, detail="Slug not found")
    
    expiration_time = datetime.utcnow() - timedelta(seconds=5)
    if slug_entry.created_at < expiration_time:
        raise HTTPException(status_code=400, detail="Slug has expired")
    
    if slug_entry.used:
        raise HTTPException(status_code=400, detail="Slug has already been used")
    
    return {"valid": True}

@app.post("/use/{slug}")
async def use_slug(slug: str):
    """Mark a slug as used"""
    db = SessionLocal()
    slug_entry = db.query(Slug).filter(Slug.slug == slug).first()
    
    if not slug_entry:
        raise HTTPException(status_code=404, detail="Slug not found")
    
    expiration_time = datetime.utcnow() - timedelta(seconds=5)
    if slug_entry.created_at < expiration_time:
        raise HTTPException(status_code=400, detail="Slug has expired")
    
    if slug_entry.used:
        raise HTTPException(status_code=400, detail="Slug has already been used")
    
    slug_entry.used = True
    db.commit()
    db.close()
    
    return {"message": "Slug successfully used"}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/content/{slug}")
async def view_content(request: Request, slug: str):
    """View protected content using a slug"""
    db = SessionLocal()
    slug_entry = db.query(Slug).filter(Slug.slug == slug).first()
    
    if not slug_entry:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error_message": "Link não encontrado"},
            status_code=404
        )
    
    expiration_time = datetime.utcnow() - timedelta(seconds=5)
    if slug_entry.created_at < expiration_time:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error_message": "Este link expirou"},
            status_code=400
        )
    
    if slug_entry.used:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "error_message": "Este link já foi utilizado"},
            status_code=400
        )
    
    # Mark slug as used
    slug_entry.used = True
    db.commit()
    db.close()
    
    return templates.TemplateResponse("protected_content.html", {"request": request})

@app.get("/pagina/{nome}", response_class=HTMLResponse)
async def pagina(request: Request, nome: str):
    return templates.TemplateResponse(f"{nome}.html", {"request": request})

# Add documentation about how to run the system
"""
How to run the system:

1. Install required packages:
   pip install fastapi sqlalchemy uvicorn

2. Run the application:
   uvicorn main:app --reload

3. API Endpoints:
   - GET /generate-slug : Generate a new unique slug
   - GET /validate/{slug} : Validate if a slug is valid and not expired
   - POST /use/{slug} : Mark a slug as used

The system uses SQLite as the database, which will be automatically created
as 'slugs.db' in the same directory when you first run the application.

The slugs expire after 5 seconds from creation and can only be used once.
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
