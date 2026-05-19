#!/usr/bin/env bash
# ═══════════════════════════════════════════════
# package.sh — Create a clean zip for sharing
# ═══════════════════════════════════════════════
#
# Usage:
#   ./package.sh
#
# Creates: aws-provisioner.zip (excludes all generated files)
# ═══════════════════════════════════════════════

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
OUTPUT_FILE="$HOME/Desktop/aws-provisioner.zip"

cd "$(dirname "$PROJECT_ROOT")"

echo "📦 Packaging project..."
echo "   Excluding: .venv, node_modules, .next, .terraform, __pycache__, .git"

zip -r "$OUTPUT_FILE" "$PROJECT_NAME" \
    -x "$PROJECT_NAME/.venv/*" \
    -x "$PROJECT_NAME/.venv/**" \
    -x "$PROJECT_NAME/web-ui/frontend/node_modules/*" \
    -x "$PROJECT_NAME/web-ui/frontend/node_modules/**" \
    -x "$PROJECT_NAME/web-ui/frontend/.next/*" \
    -x "$PROJECT_NAME/web-ui/frontend/.next/**" \
    -x "$PROJECT_NAME/.terraform/*" \
    -x "$PROJECT_NAME/.terraform/**" \
    -x "$PROJECT_NAME/.git/*" \
    -x "$PROJECT_NAME/.git/**" \
    -x "$PROJECT_NAME/__pycache__/*" \
    -x "$PROJECT_NAME/**/__pycache__/*" \
    -x "$PROJECT_NAME/.pytest_cache/*" \
    -x "$PROJECT_NAME/.pytest_cache/**" \
    -x "$PROJECT_NAME/.coverage" \
    -x "$PROJECT_NAME/.DS_Store" \
    -x "$PROJECT_NAME/**/.DS_Store" \
    -x "*.pyc" \
    | tail -1

ZIP_SIZE=$(du -sh "$OUTPUT_FILE" | awk '{print $1}')
echo ""
echo "✅ Created: $OUTPUT_FILE ($ZIP_SIZE)"
echo ""
echo "Your friend should:"
echo "  1. Unzip the file"
echo "  2. cd into the project folder"
echo "  3. Run: chmod +x setup.sh && ./setup.sh"
echo "  4. Run: ./start.sh"
echo "  5. Open: http://localhost:3000"
