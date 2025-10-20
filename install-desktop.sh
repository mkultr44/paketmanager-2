#!/bin/bash
set -e

if [[ $EUID -ne 0 ]]; then
  echo "Bitte als root ausführen (sudo ./install.sh)"
  exit 1
fi

USER_NAME="aralpi"
if id "dietpi" &>/dev/null; then
  USER_NAME="dietpi"
fi

echo "🚀 Installation Hermes Paketmanager (Raspberry Pi OS 64-bit)"

apt update
apt install -y python3 python3-pip python3-venv python3-dev \
  libgl1-mesa-dev libgles2-mesa-dev \
  libgstreamer1.0-dev gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
  libmtdev-dev libportmidi-dev xinput mesa-utils git build-essential cmake \
  libjpeg-dev zlib1g-dev

gpu_mem=$(vcgencmd get_mem gpu 2>/dev/null | cut -d'=' -f2 | cut -d'M' -f1 || echo 0)
if (( gpu_mem < 128 )); then
  echo "⚙️  Setze gpu_mem=128"
  if ! grep -q "^gpu_mem" /boot/config.txt; then
    echo "gpu_mem=128" >> /boot/config.txt
  else
    sed -i 's/^gpu_mem=.*/gpu_mem=128/' /boot/config.txt
  fi
fi

install_dir="/opt/paketmanager"
mkdir -p "$install_dir"
cp -r ./* "$install_dir"
chown -R "$USER_NAME":"$USER_NAME" "$install_dir"
cd "$install_dir"

echo "🐍 Erstelle virtuelle Umgebung ..."
sudo -u "$USER_NAME" python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel Cython

echo "📦 Baue Kivy 2.3.0 aus Source (Dauert 15–30 min auf Pi 4)"
pip install "kivy[base] @ git+https://github.com/kivy/kivy.git@2.3.0"

pip install -r requirements.txt || true

# Touchscreen-Kalibrierung 1200×800
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

raspi-config nonint do_boot_behaviour B4

echo "✅ Installation abgeschlossen – App startet automatisch nach Login"
