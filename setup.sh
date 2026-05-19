#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# setup.sh — One-command setup for AWS Provisioning System
# ═══════════════════════════════════════════════════════════
#
# Usage:
#   chmod +x setup.sh && ./setup.sh
#
# This script will:
#   1. Check system prerequisites (Python 3.10+, Node.js 18+, npm)
#   2. Create a Python virtual environment & install backend deps
#   3. Install frontend Node.js dependencies
#   4. Verify everything is working
#   5. Print instructions to start the app
#
# Works on: macOS (Intel & Apple Silicon), Linux (Ubuntu/Debian)
# ═══════════════════════════════════════════════════════════

set -e

# ── Colors ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Helpers ──
info()    { echo -e "${BLUE}ℹ${NC}  $1"; }
success() { echo -e "${GREEN}✓${NC}  $1"; }
warn()    { echo -e "${YELLOW}⚠${NC}  $1"; }
fail()    { echo -e "${RED}✗${NC}  $1"; exit 1; }
step()    { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}"; }

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║  AWS Provisioner — Project Setup                     ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# ═══════════════════════════════════════════════
# Step 1: Check Prerequisites
# ═══════════════════════════════════════════════
step "Step 1/4 — Checking Prerequisites"

# Python
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 10 ]; then
        success "Python $PY_VERSION found"
    else
        fail "Python 3.10+ required (found $PY_VERSION). Install from https://python.org"
    fi
else
    fail "Python 3 not found. Install from https://python.org or: brew install python"
fi

# Node.js
if command -v node &>/dev/null; then
    NODE_VERSION=$(node --version | sed 's/v//')
    NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
    if [ "$NODE_MAJOR" -ge 18 ]; then
        success "Node.js v$NODE_VERSION found"
    else
        fail "Node.js 18+ required (found v$NODE_VERSION). Install from https://nodejs.org"
    fi
else
    fail "Node.js not found. Install from https://nodejs.org or: brew install node"
fi

# npm
if command -v npm &>/dev/null; then
    NPM_VERSION=$(npm --version)
    success "npm $NPM_VERSION found"
else
    fail "npm not found. It should come with Node.js."
fi

# Optional tools (nice to have, not required for the Web UI)
echo ""
info "Checking optional tools..."

if command -v terraform &>/dev/null; then
    TF_VERSION=$(terraform version -json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['terraform_version'])" 2>/dev/null || terraform version | head -1 | awk '{print $2}')
    success "Terraform $TF_VERSION found (optional — for deployments)"
else
    warn "Terraform not installed (optional — Web UI works without it)"
    info "  Install: brew install terraform  OR  https://terraform.io/downloads"
fi

if command -v aws &>/dev/null; then
    success "AWS CLI found (optional — for cloud operations)"
else
    warn "AWS CLI not installed (optional — Web UI works without it)"
    info "  Install: brew install awscli  OR  https://aws.amazon.com/cli/"
fi

if command -v opa &>/dev/null; then
    success "OPA found (optional — for Rego policy evaluation)"
else
    warn "OPA not installed (optional — YAML policies still work)"
    info "  Install: brew install opa"
fi

if command -v infracost &>/dev/null; then
    success "Infracost found (optional — for cost estimation)"
else
    warn "Infracost not installed (optional — cost estimation will show N/A)"
    info "  Install: brew install infracost"
fi

# ═══════════════════════════════════════════════
# Step 2: Python Backend Setup
# ═══════════════════════════════════════════════
step "Step 2/4 — Setting up Python Backend"

# Create virtual environment
if [ -d ".venv" ]; then
    info "Virtual environment .venv already exists"
else
    info "Creating Python virtual environment..."
    python3 -m venv .venv
    success "Virtual environment created at .venv/"
fi

# Activate and install
info "Installing Python dependencies..."
".venv/bin/pip" install --upgrade pip --quiet 2>/dev/null
".venv/bin/pip" install -r requirements.txt --quiet
".venv/bin/pip" install -r web-ui/api/requirements.txt --quiet
".venv/bin/pip" install 'uvicorn[standard]' --quiet
success "Python dependencies installed"

# Verify critical imports
".venv/bin/python" -c "import fastapi, uvicorn, yaml, websockets; print('All imports OK')" 2>/dev/null \
    && success "Backend imports verified" \
    || fail "Some Python packages failed to import"

# ═══════════════════════════════════════════════
# Step 3: Frontend Setup
# ═══════════════════════════════════════════════
step "Step 3/4 — Setting up Frontend"

cd "$PROJECT_ROOT/web-ui/frontend"

if [ -d "node_modules" ]; then
    info "node_modules already exists, checking for updates..."
fi

info "Installing Node.js dependencies (this may take a minute)..."
npm install --silent 2>&1 | tail -3
success "Frontend dependencies installed"

cd "$PROJECT_ROOT"

# ═══════════════════════════════════════════════
# Step 4: Verify Everything
# ═══════════════════════════════════════════════
step "Step 4/4 — Verification"

# Run Python tests
info "Running test suite..."
TEST_OUTPUT=$(".venv/bin/python" -m pytest tests/ -q --tb=no 2>&1 | tail -1)
if echo "$TEST_OUTPUT" | grep -q "passed"; then
    success "Tests: $TEST_OUTPUT"
else
    warn "Some tests may have failed: $TEST_OUTPUT"
fi

# Verify Next.js build
info "Checking frontend compilation..."
cd "$PROJECT_ROOT/web-ui/frontend"
BUILD_OUTPUT=$(npx next build 2>&1 | tail -3)
if echo "$BUILD_OUTPUT" | grep -q "Static"; then
    success "Frontend compiles successfully"
else
    warn "Frontend build had issues — try 'npm run dev' to see details"
fi

cd "$PROJECT_ROOT"

# ═══════════════════════════════════════════════
# Done!
# ═══════════════════════════════════════════════
echo ""
echo -e "${BOLD}${GREEN}══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}  ✓ Setup Complete!${NC}"
echo -e "${BOLD}${GREEN}══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BOLD}To start the application, open TWO terminals:${NC}"
echo ""
echo -e "${CYAN}Terminal 1 — Backend API Server:${NC}"
echo -e "  cd $(basename "$PROJECT_ROOT")/web-ui/api"
echo -e "  ${YELLOW}../../.venv/bin/uvicorn server:app --reload --port 8000${NC}"
echo ""
echo -e "${CYAN}Terminal 2 — Frontend Dev Server:${NC}"
echo -e "  cd $(basename "$PROJECT_ROOT")/web-ui/frontend"
echo -e "  ${YELLOW}npm run dev${NC}"
echo ""
echo -e "${BOLD}Then open: ${CYAN}http://localhost:3000${NC}"
echo ""
echo -e "${BOLD}Login credentials:${NC}"
echo -e "  Any username from the teams.yaml file (e.g. ${YELLOW}Eternal-prithivi${NC})"
echo -e "  No password required — username lookup only."
echo ""
echo -e "${BOLD}To run tests:${NC}"
echo -e "  ${YELLOW}.venv/bin/python -m pytest tests/ -v${NC}"
echo ""
