#!/bin/bash
set -e

echo "🔧 Wende Hermes-Service-Patch an (Benutzer: aralpi)..."

INSTALL_DIR="/opt/paketmanager"
SERVICE_FILE="/etc/systemd/system/hermes.service"
USER_NAME="aralpi"

# --- Prüfen, ob App existiert ---
if [[ ! -d "$INSTALL_DIR" ]]; then
  echo "❌ Verzeichnis $INSTALL_DIR wurde nicht gefunden. Bitte zuerst die App installieren."
  exit 1
fi

if [[ ! -f "$INSTALL_DIR/app.py" ]]; then
  echo "❌ Keine app.py gefunden unter $INSTALL_DIR"
  exit 1
fi

# --- Falls alter Desktop-Autostart existiert, deaktivieren ---
AUTOSTART_FILE="/home/$USER_NAME/.config/autostart/hermes.desktop"
if [[ -f "$AUTOSTART_FILE" ]]; then
  echo "🗑️  Entferne alten Desktop-Autostart..."
  rm -f "$AUTOSTART_FILE"
fi

# --- Neues systemd-Service-File schreiben ---
echo "⚙️  Erstelle systemd-Service unter $SERVICE_FILE ..."

cat >"$SERVICE_FILE" <<EOF
[Unit]
Description=Hermes Paketmanager (Kioskmodus)
After=graphical.target

[Service]
User=$USER_NAME
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/app.py
Restart=always
RestartSec=5
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$USER_NAME/.Xauthority

[Install]
WantedBy=graphical.target
EOF

# --- Berechtigungen setzen ---
chmod 644 "$SERVICE_FILE"
systemctl daemon-reload

# --- Aktivieren und starten ---
systemctl enable hermes.service
systemctl restart hermes.service

# --- Statusausgabe ---
sleep 1
echo "✅ Hermes-Service aktiviert und gestartet."
systemctl --no-pager --quiet is-active hermes.service && echo "🟢 Läuft unter systemd" || echo "⚠️  Service läuft nicht korrekt."

echo
echo "📁 Installationspfad: $INSTALL_DIR"
echo "🧩 Service-Datei: $SERVICE_FILE"
echo "🧠 Neustart bei Absturz: Aktiv"
echo
echo "ℹ️  Logs ansehen mit:"
echo "    journalctl -u hermes.service -f"
