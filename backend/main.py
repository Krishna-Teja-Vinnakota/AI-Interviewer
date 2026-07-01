"""FastAPI application entry point."""
import os
import webbrowser
import threading
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from core.database import connect_to_mongo, close_mongo_connection
from api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def open_browser():
    """Open browser after a short delay."""
    import time
    time.sleep(2)
    try:
        webbrowser.open("http://localhost:8000/")
        logger.info("Browser opened successfully")
    except Exception as e:
        logger.warning(f"Could not open browser automatically: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    try:
        await connect_to_mongo()
        
        # Check SMTP configuration (MANDATORY)
        from core.config import settings
        if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("="*60)
            logger.warning("⚠️  SMTP NOT CONFIGURED - EMAIL IS MANDATORY!")
            logger.warning("="*60)
            logger.warning("The system requires email configuration to work.")
            logger.warning("Please configure SMTP settings in backend/.env:")
            logger.warning("  SMTP_HOST=smtp.gmail.com")
            logger.warning("  SMTP_PORT=587")
            logger.warning("  SMTP_USER=your.email@gmail.com")
            logger.warning("  SMTP_PASSWORD=your_app_password")
            logger.warning("  SMTP_TLS=True")
            logger.warning("")
            logger.warning("See EMAIL_SETUP.txt for detailed instructions.")
            logger.warning("="*60)
        else:
            logger.info("✅ SMTP configured - Email service ready")
            logger.info(f"   SMTP Host: {settings.SMTP_HOST}")
            logger.info(f"   SMTP User: {settings.SMTP_USER}")
        
        logger.info("Application startup complete")
        
        # Open browser in a separate thread
        threading.Thread(target=open_browser, daemon=True).start()
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        await close_mongo_connection()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Create FastAPI app
app = FastAPI(
    title="AI Interview System API",
    description="Backend API for AI-powered interview system",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get frontend directory path
current_dir = Path(__file__).parent
frontend_dir = current_dir.parent / "frontend"

# Mount static files
if frontend_dir.exists():
    app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(frontend_dir / "js")), name="js")

# Include API routers
app.include_router(router)


@app.get("/")
async def root():
    """Serve frontend index.html."""
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {
        "message": "AI Interview System API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/recruiter.html")
async def recruiter_page():
    """Serve recruiter page."""
    return FileResponse(str(frontend_dir / "recruiter.html"))


@app.get("/candidate.html")
async def candidate_page():
    """Serve candidate page."""
    return FileResponse(str(frontend_dir / "candidate.html"))


@app.get("/interview.html")
async def interview_page():
    """Serve interview page."""
    return FileResponse(str(frontend_dir / "interview.html"))
