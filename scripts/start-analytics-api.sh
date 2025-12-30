#!/bin/bash

# =============================================================================
# Start Analytics API Service
# =============================================================================
#
# This script starts the FastAPI analytics service that provides REST endpoints
# for accessing Langfuse data. The frontend uses this service to display ROI
# and cost analytics.
#
# Prerequisites:
#   1. Langfuse must be running (local Docker or cloud)
#   2. Environment variables must be configured in apps/backend/.env
#
# Usage:
#   ./scripts/start-analytics-api.sh         # Start with default port 8100
#   ./scripts/start-analytics-api.sh 8200    # Start with custom port
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/apps/backend"

# Default port
PORT="${1:-8100}"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Auto-Claude Analytics API Service                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if we're in the right directory
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}Error: Backend directory not found at $BACKEND_DIR${NC}"
    exit 1
fi

cd "$BACKEND_DIR"

# Check for virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Load .env file if it exists
if [ -f ".env" ]; then
    echo -e "${GREEN}Loading environment from .env${NC}"
    export $(grep -v '^#' .env | xargs)
fi

# Check Langfuse configuration
if [ -z "$LANGFUSE_PUBLIC_KEY" ] || [ -z "$LANGFUSE_SECRET_KEY" ]; then
    echo -e "${YELLOW}Warning: Langfuse API keys not configured${NC}"
    echo -e "${YELLOW}The analytics API will start but won't be able to fetch data.${NC}"
    echo ""
    echo "To configure Langfuse, add to apps/backend/.env:"
    echo "  LANGFUSE_ENABLED=true"
    echo "  LANGFUSE_PUBLIC_KEY=pk-lf-xxx"
    echo "  LANGFUSE_SECRET_KEY=sk-lf-xxx"
    echo "  LANGFUSE_HOST=http://localhost:3001"
    echo ""
fi

# Check if port is in use
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}Warning: Port $PORT is already in use${NC}"
    echo "Use a different port: ./scripts/start-analytics-api.sh <port>"
    exit 1
fi

echo -e "${GREEN}Starting Analytics API on port $PORT...${NC}"
echo ""
echo "Endpoints:"
echo "  - Health: http://localhost:$PORT/health"
echo "  - Traces: http://localhost:$PORT/api/analytics/traces"
echo "  - ROI:    http://localhost:$PORT/api/analytics/roi/summary"
echo "  - Costs:  http://localhost:$PORT/api/analytics/costs"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop${NC}"
echo ""

# Start the FastAPI server
ANALYTICS_API_PORT=$PORT python -m uvicorn analytics.api.app:app --host 0.0.0.0 --port $PORT --reload
