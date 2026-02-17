from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.api import api_router
from app.services.scheduler import start_scheduler, stop_scheduler
import atexit

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Personal Finance Portfolio Tracker API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


# Startup event to start the background scheduler
@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup"""
    start_scheduler()


# Shutdown event to stop the background scheduler
@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks on application shutdown"""
    stop_scheduler()


# Register cleanup on exit
atexit.register(stop_scheduler)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to PortAct API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

# Made with Bob
