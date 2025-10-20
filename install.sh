#!/bin/bash
set -e

# Root-Rechte prüfen
if [[ $EUID -ne 0 ]]; then
  echo "Bitte als root ausführen (sudo ./install.sh)"
  exit 1
fi

# --- Pakete installieren ---
apt update
apt install -y python3-venv python3-pip python3-dev build-essential \
  libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
  libportmidi-dev libmtdev-dev libgl1-mesa-dev libgles2-mesa-dev \
  libgstreamer1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  zlib1g-dev libjpeg-dev

# --- Projektverzeichnis anlegen ---
install_dir="/opt/paketmanager"
mkdir -p "$install_dir"

# --- Dateien kopieren ---
cp -r ./* "$install_dir"
cd "$install_dir"

# --- Virtuelle Umgebung ---
python3 -m venv venv
source venv/bin/activate

# --- Pip aktualisieren und requirements installieren ---
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Installation abgeschlossen unter $install_dir"

# --- Systemd-Service installieren ---
if [[ -f "hermes.service" ]]; then
  cp hermes.service /etc/systemd/system/hermes.service
  systemctl daemon-reload
  systemctl enable hermes.service
  systemctl start hermes.service
  echo "✅ hermes.service aktiviert und gestartet"
else
  echo "⚠️  Keine hermes.service-Datei gefunden – bitte manuell hinzufügen"
fi

systemctl status hermes.service --no-pager || true
