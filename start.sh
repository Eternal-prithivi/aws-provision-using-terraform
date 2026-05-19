#!/usr/bin/env bash
# ═══════════════════════════════════════════════
# start.sh — Launch the complete application
# ═══════════════════════════════════════════════
#
# Usage:
#   ./start.sh          # Starts both backend + frontend
#   ./start.sh --stop   # Kills both servers
#
# Prerequisites: Run ./setup.sh first!
# ═══════════════════════════════════════════════

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Stop mode ──
if [ "$1" = "--stop" ]; then
    echo -e "${YELLOW}Stopping servers...${NC}"
    lsof -i :8000 -t 2>/dev/null | xargs kill -9 2>/dev/null && echo -e "${GREEN}✓ Backend stopped${NC}" || echo -e "${CYAN}ℹ Backend was not running${NC}"
    lsof -i :3000 -t 2>/dev/null | xargs kill -9 2>/dev/null && echo -e "${GREEN}✓ Frontend stopped${NC}" || echo -e "${CYAN}ℹ Frontend was not running${NC}"
    exit 0
fi

# ── Check setup ──
if [ ! -d ".venv" ]; then
    echo -e "${RED}✗ Virtual environment not found. Run ./setup.sh first!${NC}"
    exit 1
fi
if [ ! -d "web-ui/frontend/node_modules" ]; then
    echo -e "${RED}✗ Node modules not found. Run ./setup.sh first!${NC}"
    exit 1
fi

# ── Kill any existing servers ──
lsof -i :8000 -t 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -i :3000 -t 2>/dev/null | xargs kill -9 2>/dev/null || true
sleep 1

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║  AWS Provisioner — Starting...           ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Start Backend ──
echo -e "${CYAN}Starting backend API server (port 8000)...${NC}"
cd "$PROJECT_ROOT/web-ui/api"
"$PROJECT_ROOT/.venv/bin/uvicorn" server:app --reload --port 8000 &
BACKEND_PID=$!
cd "$PROJECT_ROOT"

# Wait for backend to be ready
for i in {1..10}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready${NC}"
        break
    fi
    sleep 1
done

# ── Start Frontend ──
echo -e "${CYAN}Starting frontend dev server (port 3000)...${NC}"
cd "$PROJECT_ROOT/web-ui/frontend"
npm run dev &
FRONTEND_PID=$!
cd "$PROJECT_ROOT"

sleep 3
echo ""
echo -e "${BOLD}${GREEN}══════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  ✓ Application is running!${NC}"
echo -e "${BOLD}${GREEN}══════════════════════════════════════════${NC}"
echo ""
echo -e "  ${BOLD}Open:${NC} ${CYAN}http://localhost:3000${NC}"
echo -e "  ${BOLD}API:${NC}  ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop both servers"
echo ""

# ── Wait and handle Ctrl+C ──
trap "echo ''; echo -e '${YELLOW}Shutting down...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
