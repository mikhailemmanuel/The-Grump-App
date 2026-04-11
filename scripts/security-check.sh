#!/usr/bin/env bash
set -e
echo "=== Backend dependency audit ==="
cd backend
pip-audit 2>/dev/null || echo "pip-audit not installed — run: pip install pip-audit"
cd ..
echo ""
echo "=== Mobile dependency audit ==="
cd mobile
npm audit 2>/dev/null || echo "npm not available or node_modules missing"
cd ..
echo "=== Done ==="
