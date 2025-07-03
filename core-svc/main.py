"""
FastAPI Application - YouTube Shorts Editor Core Service
Phase 1: Foundation & Infrastructure
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import structlog

from .api.routes import router as api_router
from .api.edl_routes import router as edl_router
from .models.database import engine, Base
from .utils.logging import setup_logging

# Configure structured logging
setup_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting YouTube Shorts Editor Core Service")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Core Service")


def create_app() -> FastAPI:
    """Application factory"""
    app = FastAPI(
        title="YouTube Shorts Editor",
        description="AI-powered video editing service with manual controls",
        version="1.0.0-phase1",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )
    
    # CORS middleware for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # Next.js dev server
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(edl_router, prefix="/api/v1")
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "youtube-shorts-editor",
            "version": "1.0.0-phase1"
        }
    
    return app


# Create app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)