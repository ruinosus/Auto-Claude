"""
FastAPI Application for ROI Engine.

Provides REST API for:
- ROI calculation (by spec, trace, project)
- Artifact listing and valuation
- Configuration (rates, artifact types, roles)
"""

# Load environment variables from backend .env BEFORE other imports
import os
from pathlib import Path

# Find backend .env file and load it
_backend_env = Path(__file__).parent.parent.parent / "backend" / ".env"
if _backend_env.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_backend_env)
    except ImportError:
        # Fallback: parse .env manually if dotenv not installed
        with open(_backend_env) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import (
    roi_router,
    artifacts_router,
    costs_router,
    quality_router,
    traces_router,
    benchmarks_router,
    forecasts_router,
    time_saved_router,
    satisfaction_router,
    migration_router,
    config_router,
    health_router,
    metrics_router,
)
from .models import HealthResponse

# Try to import Langfuse integration to check availability
try:
    import sys
    _backend_path = Path(__file__).parent.parent.parent / "backend"
    if str(_backend_path) not in sys.path:
        sys.path.insert(0, str(_backend_path))
    from analytics.langfuse_integration import is_langfuse_ready
    LANGFUSE_CHECK_AVAILABLE = True
except ImportError:
    LANGFUSE_CHECK_AVAILABLE = False
    def is_langfuse_ready() -> bool:
        return False


app = FastAPI(
    title="ROI Engine API",
    description="""
    Artifact-based ROI calculation for Auto-Claude.

    The ROI Engine tracks the real value Auto-Claude generates by measuring
    artifacts produced against token costs using the formula:

    ROI = (Artifact Value - Token Cost) / Token Cost × 100%

    Each artifact is valued based on the role that would produce it
    and the estimated time required.
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include API routes - each router has its own prefix
app.include_router(roi_router, prefix="/api")
app.include_router(artifacts_router, prefix="/api")
app.include_router(costs_router, prefix="/api")
app.include_router(quality_router, prefix="/api")
app.include_router(traces_router, prefix="/api")
app.include_router(benchmarks_router, prefix="/api")
app.include_router(forecasts_router, prefix="/api")
app.include_router(time_saved_router, prefix="/api")
app.include_router(satisfaction_router, prefix="/api")
app.include_router(migration_router, prefix="/api")
app.include_router(config_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": "ROI Engine API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    langfuse_available = False
    if LANGFUSE_CHECK_AVAILABLE:
        try:
            langfuse_available = is_langfuse_ready()
        except Exception:
            pass

    return HealthResponse(
        status="ok",
        version="0.1.0",
        langfuse_available=langfuse_available,
    )


# For running directly with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
