#!/bin/bash
set -e

# --- Root-Rechte prüfen ---
if [[ $EUID -ne 0 ]]; then
  echo "Bitte als root ausführen (sudo ./install.sh)"
  exit 1
fi

# --- Benutzer bestimmen ---
DEFAULT_USER="dietpi"
if id "pi" &>/dev/null; then
  DEFAULT_USER="pi"
fi
USER_NAME="$DEFAULT_USER"

echo "🚀 Starte Installation des Hermes Paketmanagers für Benutzer '$USER_NAME' ..."

# --- Basis-Pakete installieren ---
apt update
apt install -y python3.11 python3.11-venv python3.11-dev build-essential \
  libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
  libportmidi-dev libmtdev-dev libgl1-mesa-dev libgles2-mesa-dev \
  libgstreamer1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  xserver-xorg xinit xinput mesa-utils libjpeg-dev zlib1g-dev

# --- GPU-Speicher prüfen (mind. 64 MB) ---
gpu_mem=$(vcgencmd get_mem gpu 2>/dev/null | cut -d'=' -f2 | cut -d'M' -f1 || echo 0)
if (( gpu_mem < 64 )); then
  echo "⚙️  Setze GPU Memory Split auf 128 MB ..."
  if ! grep -q "^gpu_mem" /boot/config.txt; then
    echo "gpu_mem=128" >> /boot/config.txt
  else
    sed -i 's/^gpu_mem=.*/gpu_mem=128/' /boot/config.txt
  fi
fi

# --- Projektverzeichnis ---
install_dir="/opt/paketmanager"
mkdir -p "$install_dir"
cp -r ./* "$install_dir"
chown -R "$USER_NAME":"$USER_NAME" "$install_dir"
cd "$install_dir"

# --- Virtuelle Umgebung (Python 3.11) ---
echo "🐍 Erstelle virtuelle Umgebung ..."
sudo -u "$USER_NAME" python3.11 -m venv venv
source venv/bin/activate

# --- Kivy + Requirements ---
pip install --upgrade pip setuptools wheel Cython
pip install kivy==2.3.0
pip install -r requirements.txt || true

echo "✅ Python-Umgebung und Kivy installiert"

# --- Xorg Touchscreen-Kalibrierung (1200x800) ---
mkdir -p /usr/share/X11/xorg.conf.d
cat >/usr/share/X11/xorg.conf.d/99-touchscreen.conf <<'EOF'
Section "Monitor"
    Identifier "DefaultMonitor"
    Option "DPMS" "false"
EndSection

Section "Screen"
    Identifier "DefaultScreen"
    Monitor "DefaultMonitor"
EndSection

Section "ServerLayout"
    Identifier "Layout0"
    Screen "DefaultScreen"
EndSection

Section "InputClass"
    Identifier "Touchscreen"
    MatchIsTouchscreen "on"
    Option "Calibration" "0 1200 800 0"
    Option "SwapAxes" "0"
EndSection
EOF

echo "✅ X11-Touchscreen-Konfiguration gesetzt (1200x800)"

# --- Systemd-Service für Direktstart über X11 ---
cat >/etc/systemd/system/hermes.service <<EOF
[Unit]
Description=Hermes Paket Einlagerungssystem (Direct X11)
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$install_dir
ExecStart=/usr/bin/startx $install_dir/venv/bin/python $install_dir/app.py --
Environment=DISPLAY=:0
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hermes.service
systemctl start hermes.service

echo "✅ hermes.service aktiviert und gestartet"

# --- Automatische Anmeldung aktivieren ---
echo "⚙️  Aktiviere automatische Anmeldung für Benutzer '$USER_NAME' ..."
AUTOLOGIN_CONF="/etc/systemd/system/getty@tty1.service.d/autologin.conf"
mkdir -p "$(dirname "$AUTOLOGIN_CONF")"
cat >"$AUTOLOGIN_CONF" <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $USER_NAME --noclear %I \$TERM
EOF

systemctl daemon-reexec
systemctl restart getty@tty1.service || true

echo "✅ Automatische Anmeldung aktiviert"
echo "✅ Installation abgeschlossen – App läuft im Vollbild (1200x800 Touchscreen)"
echo "📁 Installationspfad: $install_dir"
