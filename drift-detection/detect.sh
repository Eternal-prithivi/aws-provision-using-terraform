#!/usr/bin/env bash
# drift-detection/detect.sh — Infrastructure Drift Detection Script
#
# Runs terraform plan and checks for unexpected changes.
# If drift is detected, generates drift-report.txt and exits with code 2.
# If no drift, exits with code 0.
#
# Usage:
#   bash drift-detection/detect.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORT_FILE="$PROJECT_ROOT/drift-report.txt"
TIMESTAMP=$(date -u +"%Y-%m-%d %H:%M:%S UTC")

echo ""
echo "  🔍 Drift Detection — $TIMESTAMP"
echo "  ─────────────────────────────────────"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Check terraform is available
if ! command -v terraform &> /dev/null; then
    echo "  ❌ terraform is not installed"
    exit 1
fi

# Run terraform init (quiet mode)
echo "  ▶️  Initializing..."
if ! terraform init -input=false -no-color > /dev/null 2>&1; then
    echo "  ❌ terraform init failed"
    exit 1
fi

# Run terraform plan and capture output
echo "  ▶️  Scanning for drift..."
echo ""
PLAN_OUTPUT=$(terraform plan -input=false -detailed-exitcode -no-color 2>&1) || PLAN_EXIT_CODE=$?
PLAN_EXIT_CODE=${PLAN_EXIT_CODE:-0}

# terraform plan exit codes:
#   0 = No changes (no drift)
#   1 = Error
#   2 = Changes detected (drift found)

if [ "$PLAN_EXIT_CODE" -eq 0 ]; then
    echo "  ✅ No drift detected"
    echo "     Infrastructure matches Terraform code perfectly."
    echo ""
    echo "Report: No drift detected at $TIMESTAMP" > "$REPORT_FILE"
    exit 0

elif [ "$PLAN_EXIT_CODE" -eq 2 ]; then
    echo "  ⚠️  DRIFT DETECTED!"
    echo ""

    # Count changes
    ADDS=$(echo "$PLAN_OUTPUT" | grep -c "will be created" || true)
    CHANGES=$(echo "$PLAN_OUTPUT" | grep -c "will be updated" || true)
    DESTROYS=$(echo "$PLAN_OUTPUT" | grep -c "will be destroyed" || true)
    echo "  Summary: +$ADDS to create, ~$CHANGES to update, -$DESTROYS to destroy"
    echo ""

    # Show only the affected resources (1 line each)
    echo "  Affected resources:"
    echo "$PLAN_OUTPUT" | grep -E '^\s+#' | while read -r line; do
        resource=$(echo "$line" | sed 's/^[[:space:]]*# //;s/ will be.*//;s/ must be.*//')
        action=""
        if echo "$line" | grep -q "created"; then
            action="CREATE"
        elif echo "$line" | grep -q "updated"; then
            action="UPDATE"
        elif echo "$line" | grep -q "destroyed"; then
            action="DESTROY"
        fi
        echo "    [$action] $resource"
    done
    echo ""

    echo "  To fix drift:"
    echo "    terraform apply   — Make AWS match your code"
    echo "    terraform destroy — Remove everything"
    echo ""

    # Save detailed report to file (full details only in the file)
    {
        echo "# Drift Detection Report"
        echo "Timestamp: $TIMESTAMP"
        echo "Status: DRIFT DETECTED"
        echo "Summary: +$ADDS to create, ~$CHANGES to update, -$DESTROYS to destroy"
        echo ""
        echo "## Affected Resources"
        echo "$PLAN_OUTPUT" | grep -E '^\s+#' | sed 's/^[[:space:]]*# /  /'
        echo ""
        echo "## Full Plan Output"
        echo "$PLAN_OUTPUT"
    } > "$REPORT_FILE"

    echo "  📄 Full details saved to: drift-report.txt"
    echo ""

    exit 2

else
    echo "  ❌ terraform plan failed (exit code $PLAN_EXIT_CODE)"
    echo ""

    {
        echo "# Drift Detection Report"
        echo "Timestamp: $TIMESTAMP"
        echo "Status: ERROR"
        echo ""
        echo "$PLAN_OUTPUT"
    } > "$REPORT_FILE"

    exit 1
fi
