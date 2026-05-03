#!/usr/bin/env bash
# QAMachine VPS Setup Script
# Run as root on fresh Ubuntu 22.04
# Usage: bash setup-vps.sh <domain>
# Example: bash setup-vps.sh api.qamachine.io

set -e
DOMAIN=${1:-"api.yourdomain.com"}
APP_USER="ubuntu"
REPO_DIR="/home/$APP_USER/repo"        # git clone goes here
ENGINE_DIR="$REPO_DIR/QAmachine"       # Playwright engine
SAAS_DIR="$REPO_DIR/qamachine-saas"   # FastAPI backend

echo "=== QAMachine VPS Setup ==="
echo "Domain:     $DOMAIN"
echo "Repo dir:   $REPO_DIR"

# ── 1. System packages ────────────────────────────────────────────────────────
apt-get update -q
apt-get install -y -q \
  git curl wget nginx certbot python3-certbot-nginx \
  python3.11 python3.11-venv python3.11-dev python3-pip \
  build-essential libssl-dev libffi-dev \
  libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 \
  libasound2 libxshmfence1 libgles2

echo ">>> System packages installed"

# ── 2. Clone repo ─────────────────────────────────────────────────────────────
if [ -d "$REPO_DIR" ]; then
  echo ">>> Pulling latest code..."
  sudo -u $APP_USER git -C $REPO_DIR pull
else
  echo ">>> Cloning repo..."
  sudo -u $APP_USER git clone https://github.com/danik441414-bit/QAMachine.git $REPO_DIR
fi

# ── 3. QAmachine engine venv ──────────────────────────────────────────────────
echo ">>> Setting up QAmachine engine..."
cd $ENGINE_DIR
sudo -u $APP_USER python3.11 -m venv .venv
sudo -u $APP_USER .venv/bin/pip install --upgrade pip -q
sudo -u $APP_USER .venv/bin/pip install -r requirements.txt -q

echo ">>> Installing Playwright browsers (Chromium)..."
sudo -u $APP_USER .venv/bin/playwright install chromium
sudo -u $APP_USER .venv/bin/playwright install-deps chromium

# ── 4. Backend venv ───────────────────────────────────────────────────────────
echo ">>> Setting up backend..."
cd $SAAS_DIR/backend
sudo -u $APP_USER python3.11 -m venv .venv
sudo -u $APP_USER .venv/bin/pip install --upgrade pip -q
sudo -u $APP_USER .venv/bin/pip install -r requirements.txt -q

# ── 5. Backend .env ───────────────────────────────────────────────────────────
if [ ! -f "$SAAS_DIR/backend/.env" ]; then
  cat > $SAAS_DIR/backend/.env << 'ENVEOF'
DEBUG=false
SECRET_KEY=REPLACE_WITH_RANDOM_32_CHAR_HEX
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db.XXXX.supabase.co:5432/postgres
CORS_ORIGINS=["https://YOURFRONTEND.vercel.app"]
FRONTEND_URL=https://YOURFRONTEND.vercel.app
ANTHROPIC_API_KEY=sk-ant-REPLACE
QAMACHINE_DIR=/home/ubuntu/repo/QAmachine
QAMACHINE_PYTHON=/home/ubuntu/repo/QAmachine/.venv/bin/python
QAMACHINE_RUNNER=/home/ubuntu/repo/QAmachine/run_session.py
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_PRO=
STRIPE_PRICE_TEAM=
ADMIN_EMAILS=["danik441414@gmail.com"]
ENVEOF
  chown $APP_USER:$APP_USER $SAAS_DIR/backend/.env
  chmod 600 $SAAS_DIR/backend/.env
  echo ""
  echo ">>> IMPORTANT: Edit .env with your real credentials:"
  echo "    nano $SAAS_DIR/backend/.env"
  echo "    Then run: systemctl restart qamachine-api"
fi

# ── 6. Systemd service ────────────────────────────────────────────────────────
sed "s|/home/ubuntu/qamachine-saas|$SAAS_DIR|g" \
  $SAAS_DIR/deploy/qamachine-api.service | \
  sed "s|User=ubuntu|User=$APP_USER|g" \
  > /etc/systemd/system/qamachine-api.service
systemctl daemon-reload
systemctl enable qamachine-api
echo ">>> Systemd service installed"

# ── 7. Nginx ──────────────────────────────────────────────────────────────────
sed "s/YOUR_DOMAIN/$DOMAIN/g" $SAAS_DIR/deploy/nginx-site.conf \
  > /etc/nginx/sites-available/qamachine
ln -sf /etc/nginx/sites-available/qamachine /etc/nginx/sites-enabled/qamachine
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
echo ">>> Nginx configured"

# ── 8. SSL ────────────────────────────────────────────────────────────────────
certbot --nginx -d $DOMAIN --non-interactive --agree-tos \
  -m admin@$DOMAIN --redirect && echo ">>> SSL configured" || \
  echo ">>> SSL failed — run manually: certbot --nginx -d $DOMAIN"

# ── 9. Start service ──────────────────────────────────────────────────────────
systemctl start qamachine-api
sleep 2
systemctl status qamachine-api --no-pager || true

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Setup complete!                                 ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Edit:    nano $SAAS_DIR/backend/.env"
echo "║  Logs:    journalctl -u qamachine-api -f         ║"
echo "║  Restart: systemctl restart qamachine-api        ║"
echo "║  Update:  bash $SAAS_DIR/deploy/update.sh        ║"
echo "╚══════════════════════════════════════════════════╝"
