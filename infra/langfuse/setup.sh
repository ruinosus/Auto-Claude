#!/bin/bash

# =============================================================================
# Langfuse Setup Script
# =============================================================================
#
# Manages the Langfuse Docker containers for local development.
#
# Usage:
#   ./infra/langfuse/setup.sh start   # Start Langfuse
#   ./infra/langfuse/setup.sh stop    # Stop Langfuse
#   ./infra/langfuse/setup.sh restart # Restart Langfuse
#   ./infra/langfuse/setup.sh status  # Check status
#   ./infra/langfuse/setup.sh logs    # View logs
#   ./infra/langfuse/setup.sh clean   # Remove containers and volumes
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

# Check Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        echo "Install Docker from: https://www.docker.com/products/docker-desktop"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo -e "${RED}Error: Docker is not running${NC}"
        echo "Please start Docker Desktop"
        exit 1
    fi
}

start() {
    check_docker
    echo -e "${BLUE}Starting Langfuse...${NC}"
    docker-compose up -d
    
    echo ""
    echo -e "${GREEN}Langfuse is starting...${NC}"
    echo ""
    echo "Waiting for Langfuse to be ready..."
    
    # Wait for Langfuse to be healthy
    for i in {1..30}; do
        if curl -s http://localhost:3001/api/public/health > /dev/null 2>&1; then
            echo ""
            echo -e "${GREEN}Langfuse is ready!${NC}"
            echo ""
            echo "Access Langfuse at: http://localhost:3001"
            echo ""
            echo "First time setup:"
            echo "  1. Create an account at http://localhost:3001"
            echo "  2. Create a new project"
            echo "  3. Go to Project Settings > API Keys"
            echo "  4. Copy the keys to apps/backend/.env:"
            echo ""
            echo "     LANGFUSE_ENABLED=true"
            echo "     LANGFUSE_PUBLIC_KEY=pk-lf-xxx"
            echo "     LANGFUSE_SECRET_KEY=sk-lf-xxx"
            echo "     LANGFUSE_HOST=http://localhost:3001"
            echo ""
            return 0
        fi
        sleep 2
        echo -n "."
    done
    
    echo ""
    echo -e "${YELLOW}Langfuse is taking longer than expected to start${NC}"
    echo "Check logs with: ./infra/langfuse/setup.sh logs"
}

stop() {
    echo -e "${BLUE}Stopping Langfuse...${NC}"
    docker-compose down
    echo -e "${GREEN}Langfuse stopped${NC}"
}

restart() {
    stop
    start
}

status() {
    echo -e "${BLUE}Langfuse Status:${NC}"
    docker-compose ps
    echo ""
    
    if curl -s http://localhost:3001/api/public/health > /dev/null 2>&1; then
        echo -e "${GREEN}Langfuse is running at http://localhost:3001${NC}"
    else
        echo -e "${YELLOW}Langfuse is not responding${NC}"
    fi
}

logs() {
    docker-compose logs -f
}

clean() {
    echo -e "${YELLOW}Warning: This will remove all Langfuse data!${NC}"
    read -p "Are you sure? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        echo -e "${GREEN}Langfuse containers and volumes removed${NC}"
    else
        echo "Cancelled"
    fi
}

# Main
case "${1:-}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    clean)
        clean
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|clean}"
        echo ""
        echo "Commands:"
        echo "  start   - Start Langfuse containers"
        echo "  stop    - Stop Langfuse containers"
        echo "  restart - Restart Langfuse containers"
        echo "  status  - Check container status"
        echo "  logs    - View container logs"
        echo "  clean   - Remove containers and volumes"
        exit 1
        ;;
esac
