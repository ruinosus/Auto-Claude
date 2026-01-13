#!/bin/bash

# =============================================================================
# Start ROI Engine API Service
# =============================================================================
#
# This script starts the ROI Engine FastAPI service that provides REST endpoints
# for artifact-based ROI calculation. The frontend uses this service (port 8002)
# as the primary source for all ROI and analytics data.
#
# Prerequisites:
#   1. Python 3.12+ installed
#   2. Backend virtual environment with dependencies
#
# Usage:
#   ./scripts/start-roi-engine.sh         # Start with default port 8002
#   ./scripts/start-roi-engine.sh 8003    # Start with custom port
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/apps/backend"
ROI_ENGINE_DIR="$PROJECT_ROOT/apps/roi_engine"

# Default port
PORT="${1:-8002}"

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║              Auto-Claude ROI Engine API                        ║${NC}"
echo -e "${CYAN}║          Artifact-based ROI Calculation Service                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if ROI Engine directory exists
if [ ! -d "$ROI_ENGINE_DIR" ]; then
    echo -e "${RED}Error: ROI Engine directory not found at $ROI_ENGINE_DIR${NC}"
    exit 1
fi

# Check for backend virtual environment (shared with ROI Engine)
if [ ! -d "$BACKEND_DIR/.venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    cd "$BACKEND_DIR"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    # Install ROI Engine as editable package
    pip install -e "$ROI_ENGINE_DIR"
else
    source "$BACKEND_DIR/.venv/bin/activate"
fi

# Ensure ROI Engine is installed
if ! python -c "import roi_engine" 2>/dev/null; then
    echo -e "${YELLOW}Installing ROI Engine package...${NC}"
    pip install -e "$ROI_ENGINE_DIR"
fi

cd "$ROI_ENGINE_DIR"

# Add ROI Engine to PYTHONPATH so imports work correctly
export PYTHONPATH="$ROI_ENGINE_DIR:$PYTHONPATH"

# Load .env file from backend if it exists
if [ -f "$BACKEND_DIR/.env" ]; then
    echo -e "${GREEN}Loading environment from backend/.env${NC}"
    export $(grep -v '^#' "$BACKEND_DIR/.env" | xargs)
fi

# Check if port is in use
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Port $PORT is already in use${NC}"
    echo "Use a different port: ./scripts/start-roi-engine.sh <port>"
    exit 1
fi

echo -e "${GREEN}Starting ROI Engine API on port $PORT...${NC}"
echo ""
echo -e "${BLUE}API Documentation:${NC}"
echo "  - Swagger UI: http://localhost:$PORT/docs"
echo "  - ReDoc:      http://localhost:$PORT/redoc"
echo ""
echo -e "${BLUE}Key Endpoints:${NC}"
echo "  - Health:      http://localhost:$PORT/health"
echo "  - ROI:         http://localhost:$PORT/api/roi/unified"
echo "  - Artifacts:   http://localhost:$PORT/api/artifacts"
echo "  - Costs:       http://localhost:$PORT/api/costs/daily"
echo "  - Time Saved:  http://localhost:$PORT/api/time-saved/summary"
echo ""
echo -e "${BLUE}Total Endpoints: 63${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Start the FastAPI server
python -m uvicorn api.app:app --host 0.0.0.0 --port $PORT --reload
