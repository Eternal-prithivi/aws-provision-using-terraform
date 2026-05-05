#!/usr/bin/env bash
# drift-detection/detect.sh — Infrastructure Drift Detection Script
#
# Runs terraform plan and checks for unexpected changes.
# If drift is detected, generates drift-report.txt and exits with code 2.
# If no drift, exits with code 0.
#
# Usage:
#   bash drift-detection/detect.sh
#
# Environment variables (set in GitHub Actions or locally):
#   AWS_ACCESS_KEY_ID       — AWS credentials
#   AWS_SECRET_ACCESS_KEY   — AWS credentials
#   AWS_DEFAULT_REGION      — AWS region (default: ap-south-1)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_FILE="$PROJECT_ROOT/drift-report.txt"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

echo "=============================================="
echo "  🔍 Infrastructure Drift Detection"
echo "  Timestamp: $TIMESTAMP"
echo "=============================================="
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Check terraform is available
if ! command -v terraform &> /dev/null; then
    echo "❌ ERROR: terraform is not installed or not in PATH"
    exit 1
fi

# Run terraform init (quiet mode)
echo "▶️  Running terraform init..."
if ! terraform init -input=false -no-color > /dev/null 2>&1; then
    echo "❌ ERROR: terraform init failed"
    exit 1
fi
echo "✅  terraform init complete"
echo ""

# Run terraform plan and capture output
echo "▶️  Running terraform plan (drift check)..."
PLAN_OUTPUT=$(terraform plan -input=false -detailed-exitcode -no-color 2>&1) || PLAN_EXIT_CODE=$?
PLAN_EXIT_CODE=${PLAN_EXIT_CODE:-0}

# terraform plan exit codes:
#   0 = No changes (no drift)
#   1 = Error
#   2 = Changes detected (drift found)

if [ "$PLAN_EXIT_CODE" -eq 0 ]; then
    echo "✅  No drift detected. Infrastructure matches Terraform state."
    echo ""
    echo "Report: No drift detected at $TIMESTAMP" > "$REPORT_FILE"
    exit 0

elif [ "$PLAN_EXIT_CODE" -eq 2 ]; then
    echo "⚠️  DRIFT DETECTED! Infrastructure has changed outside of Terraform."
    echo ""
    echo "─────────────────────────────────────────────"
    echo "  Drift Report"
    echo "─────────────────────────────────────────────"
    echo ""

    # Generate drift report
    {
        echo "# Drift Detection Report"
        echo "Timestamp: $TIMESTAMP"
        echo "Status: DRIFT DETECTED"
        echo ""
        echo "## Changes Detected"
        echo "$PLAN_OUTPUT" | grep -E '^\s*(#|~|\+|-|<=)' || echo "(see full plan output below)"
        echo ""
        echo "## Full Plan Output"
        echo "$PLAN_OUTPUT"
    } > "$REPORT_FILE"

    echo "  Report saved to: $REPORT_FILE"
    echo ""
    echo "  To resolve drift, run one of:"
    echo "    terraform apply    — Apply Terraform config (override manual changes)"
    echo "    terraform import   — Import manual changes into state"
    echo ""

    # Print summary of changes
    ADDS=$(echo "$PLAN_OUTPUT" | grep -c "will be created" || true)
    CHANGES=$(echo "$PLAN_OUTPUT" | grep -c "will be updated" || true)
    DESTROYS=$(echo "$PLAN_OUTPUT" | grep -c "will be destroyed" || true)
    echo "  Summary: +$ADDS added, ~$CHANGES changed, -$DESTROYS destroyed"
    echo ""

    exit 2

else
    echo "❌ ERROR: terraform plan failed with exit code $PLAN_EXIT_CODE"
    echo ""
    echo "$PLAN_OUTPUT"

    {
        echo "# Drift Detection Report"
        echo "Timestamp: $TIMESTAMP"
        echo "Status: ERROR"
        echo ""
        echo "$PLAN_OUTPUT"
    } > "$REPORT_FILE"

    exit 1
fi
