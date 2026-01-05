"""
FastAPI Analytics Application
=============================

Main FastAPI application for the analytics service.
Provides REST endpoints for accessing Langfuse data.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router
from .satisfaction_routes import satisfaction_router
from .time_saved_routes import router as time_saved_router
from .langfuse_client import LangfuseAPIClient

logger = logging.getLogger(__name__)

# Global client instance
_langfuse_client: Optional[LangfuseAPIClient] = None


def get_langfuse_client() -> Optional[LangfuseAPIClient]:
    """Get the global Langfuse API client."""
    global _langfuse_client

    # Lazy initialization if not already done
    if _langfuse_client is None:
        _langfuse_client = LangfuseAPIClient(
            public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
            secret_key=os.environ.get("LANGFUSE_SECRET_KEY", ""),
            host=os.environ.get("LANGFUSE_HOST", "http://localhost:3001"),
        )

    return _langfuse_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global _langfuse_client

    # Initialize Langfuse client on startup
    logger.info("Initializing Langfuse API client...")
    _langfuse_client = LangfuseAPIClient(
        public_key=os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
        secret_key=os.environ.get("LANGFUSE_SECRET_KEY", ""),
        host=os.environ.get("LANGFUSE_HOST", "http://localhost:3001"),
    )

    if _langfuse_client.is_configured():
        logger.info(f"Langfuse client initialized (host: {_langfuse_client.host})")
    else:
        logger.warning("Langfuse client not properly configured - check environment variables")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down analytics service...")
    _langfuse_client = None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Auto-Claude Analytics API",
        description="REST API for accessing Langfuse analytics data",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Configure CORS for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # Electron dev
            "http://localhost:5173",  # Vite dev
            "file://",  # Electron production
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    app.include_router(router, prefix="/api/analytics")
    app.include_router(satisfaction_router, prefix="/api/analytics")
    app.include_router(time_saved_router, prefix="/api/analytics")

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        client = get_langfuse_client()
        return {
            "status": "healthy",
            "langfuse_configured": client.is_configured() if client else False,
            "langfuse_host": client.host if client else None,
        }

    return app


# Default app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    port = int(os.environ.get("ANALYTICS_API_PORT", "8100"))
    uvicorn.run(app, host="0.0.0.0", port=port)
