#!/bin/bash
set -e

# --- Root-Rechte prüfen ---
if [[ $EUID -ne 0 ]]; then
  echo "Bitte als root ausführen (sudo ./install.sh)"
  exit 1
fi

# --- Benutzer bestimmen ---
DEFAULT_USER="pi"
if id "dietpi" &>/dev/null; then
  DEFAULT_USER="dietpi"
fi
USER_NAME="$DEFAULT_USER"

echo "🚀 Starte Installation des Hermes Paketmanagers für Raspberry Pi OS Desktop (Benutzer: $USER_NAME)"

# --- Systempakete aktualisieren ---
apt update
apt install -y python3.11 python3.11-venv python3.11-dev build-essential \
  libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
  libportmidi-dev libmtdev-dev libgl1-mesa-dev libgles2-mesa-dev \
  libgstreamer1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  libjpeg-dev zlib1g-dev xinput mesa-utils

# --- GPU-Speicher prüfen (mind. 128 MB empfohlen für Desktop + Kivy) ---
gpu_mem=$(vcgencmd get_mem gpu 2>/dev/null | cut -d'=' -f2 | cut -d'M' -f1 || echo 0)
if (( gpu_mem < 128 )); then
  echo "⚙️  Setze GPU Memory Split auf 128 MB ..."
  if ! grep -q "^gpu_mem" /boot/config.txt; then
    echo "gpu_mem=128" >> /boot/config.txt
  else
    sed -i 's/^gpu_mem=.*/gpu_mem=128/' /boot/config.txt
  fi
fi

# --- Projektverzeichnis vorbereiten ---
install_dir="/opt/paketmanager"
mkdir -p "$install_dir"
cp -r ./* "$install_dir"
chown -R "$USER_NAME":"$USER_NAME" "$install_dir"
cd "$install_dir"

# --- Virtuelle Umgebung einrichten ---
echo "🐍 Erstelle virtuelle Umgebung ..."
sudo -u "$USER_NAME" python3.11 -m venv venv
source venv/bin/activate

# --- Python-Pakete ---
pip install --upgrade pip setuptools wheel Cython
pip install kivy==2.3.0
pip install -r requirements.txt || true

echo "✅ Python-Umgebung und Kivy installiert"

# --- Optional: Touchscreen-Kalibrierung (1200×800) ---
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

echo "✅ X11-Touchscreen-Konfiguration gesetzt (1200×800)"

# --- Autostart-Eintrag im Benutzer-Desktop ---
AUTOSTART_DIR="/home/$USER_NAME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

cat >"$AUTOSTART_DIR/hermes.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Hermes Paketmanager
Exec=$install_dir/venv/bin/python $install_dir/app.py
X-GNOME-Autostart-enabled=true
EOF

chown "$USER_NAME":"$USER_NAME" "$AUTOSTART_DIR/hermes.desktop"

echo "✅ Autostart-Datei erstellt unter $AUTOSTART_DIR/hermes.desktop"

# --- Optional: Automatische Desktop-Anmeldung aktivieren ---
echo "⚙️  Aktiviere automatische Desktop-Anmeldung für Benutzer '$USER_NAME' ..."
raspi-config nonint do_boot_behaviour B4

echo "✅ Automatische Anmeldung im Desktop aktiviert"
echo "✅ Installation abgeschlossen – App startet automatisch im Vollbild (1200×800 Touchscreen)"
echo "📁 Installationspfad: $install_dir"
