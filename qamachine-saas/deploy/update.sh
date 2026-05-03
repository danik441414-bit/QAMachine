#!/usr/bin/env bash
# Deploy latest code to production
# Run on VPS: bash ~/repo/qamachine-saas/deploy/update.sh
set -e

REPO_DIR="/home/ubuntu/repo"

echo "=== Pulling latest code ==="
git -C $REPO_DIR pull

echo "=== Installing backend dependencies ==="
$REPO_DIR/qamachine-saas/backend/.venv/bin/pip install \
  -r $REPO_DIR/qamachine-saas/backend/requirements.txt -q

echo "=== Installing engine dependencies ==="
$REPO_DIR/QAmachine/.venv/bin/pip install \
  -r $REPO_DIR/QAmachine/requirements.txt -q

echo "=== Restarting API ==="
systemctl restart qamachine-api
sleep 2
systemctl status qamachine-api --no-pager

echo "=== Done! ==="
