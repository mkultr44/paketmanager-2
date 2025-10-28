# -*- coding: utf-8 -*-
# Hermes Paketmanager – stabile Kivy-App mit B2-Backup & Auto-Update
# Kompatibel mit bestehender pakete.db

# --- Umgebung/Runtime-Flags (Stabilität) ---
import os
os.environ.setdefault("KIVY_METRICS_DENSITY", "1.0")
os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")
os.environ.setdefault("KIVY_CLOCK", "interrupt")
os.environ.setdefault("SDL_VIDEO_X11_DGAMOUSE", "0")
os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")

import sqlite3
from datetime import datetime, timedelta

# Kivy Config (vor Kivy-Imports anpassen)
from kivy.config import Config
Config.set("graphics", "resizable", "0")
Config.set("kivy", "keyboard_mode", "systemanddock")
# Touch/Maus-Emulation komplett aus – verhindert Double-Tap
Config.set('input', 'mouse', 'disable')
Config.set('input', 'mtdev_%(name)s', '')
Config.set('input', 'hid_%(name)s', '')
Config.set('input', 'wm_touch', '')
Config.set('input', 'wm_pen', '')
Config.set('input', 'wm_%(name)s', '')
Config.set('modules', 'touchring', '')
Config.set('modules', 'touchpad', '')
Config.set('graphics', 'maxfps', '50')  # GPU-Last begrenzen

from kivy.core.window import Window
Window.size = (1200, 800)
Window.fullscreen = True

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import StringProperty, ListProperty, ObjectProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout

# --- Pfade & externe Funktionen (Backup / Update) ---
import subprocess, threading, shutil, hashlib, ssl, urllib.request, time, sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_FILE = "pakete.db"
DB_PATH = os.path.join(PROJECT_ROOT, DB_FILE)

BACKUP_DIR = "/opt/paketmanager/backup"                # lokaler Backup-Ordner für DB & app.py
RCLONE_DEST = "b2:aralbruehl-backups/paketmanager"      # rclone Remote-Ziel (einmalig per `rclone config` einrichten)
RAW_APP_URL = "https://raw.githubusercontent.com/mkultr44/paketmanager-2/main/app.py"  # Auto-Update Quelle (Branch: main)

def ensure_dirs():
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
    except Exception as e:
        print("⚠️ Konnte Backup-Verzeichnis nicht erstellen:", e)

ensure_dirs()

def _sha256_bytes(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()

def files_equal_bytes(a: bytes, b: bytes) -> bool:
    return _sha256_bytes(a) == _sha256_bytes(b)

def backup_db_async():
    """Asynchrones B2-Backup der Datenbank (blockiert UI nicht, offline-tolerant)."""
    def _run():
        try:
            ensure_dirs()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Lokale, versionierte Kopie
            if os.path.exists(DB_PATH):
                local_copy = os.path.join(BACKUP_DIR, f"pakete_{ts}.db")
                shutil.copy2(DB_PATH, local_copy)

            # Remotekopie: latest + versioniert (nur wenn rclone vorhanden)
            try:
                subprocess.run(
                    ["rclone", "copyto", DB_PATH, f"{RCLONE_DEST}/pakete.db"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60
                )
                subprocess.run(
                    ["rclone", "copyto", DB_PATH, f"{RCLONE_DEST}/pakete_{ts}.db"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60
                )
                print("✅ B2-Backup ok", ts)
            except FileNotFoundError:
                print("ℹ️ rclone nicht gefunden – B2-Upload übersprungen.")
            except Exception as e:
                print("⚠️ B2-Upload fehlgeschlagen (offline?):", e)

        except Exception as e:
            print("⚠️ Backup-Thread-Fehler:", e)

    threading.Thread(target=_run, daemon=True).start()

def check_and_update_app_async():
    """Prüft alle 30 Min GitHub auf neue app.py. Nur bei Änderung: Backup, ersetzen, Neustart.
       Offline-tolerant: bei Fehlern weiterlaufen."""
    def _run():
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(RAW_APP_URL, context=ctx, timeout=20) as resp:
                new_bytes = resp.read()

            app_path = os.path.abspath(__file__)
            with open(app_path, "rb") as f:
                cur_bytes = f.read()

            if files_equal_bytes(new_bytes, cur_bytes):
                # identisch -> kein Neustart
                return

            # Änderung erkannt: alte Datei sichern, neue übernehmen, sauber neu starten
            ensure_dirs()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_app = os.path.join(BACKUP_DIR, f"app.py.{ts}")
            shutil.copy2(app_path, backup_app)

            tmp_path = app_path + ".new"
            with open(tmp_path, "wb") as f:
                f.write(new_bytes)
            os.replace(tmp_path, app_path)

            print(f"🔄 Update installiert ({ts}), Neustart…")
            # systemd (Restart=always) startet neu
            os._exit(0)

        except Exception as e:
            # offline oder GitHub down → leise protokollieren, aber App weiterlaufen lassen
            print("ℹ️ Update-Check fehlgeschlagen (offline?):", e)

    threading.Thread(target=_run, daemon=True).start()

KV = """
#:import dp kivy.metrics.dp

<RectBtn@Button>:
    bg_color: 0.11,0.46,0.78,1
    border_color: 1,1,1,1
    background_normal: ''
    background_color: self.bg_color
    canvas.before:
        Color:
            rgba: self.border_color
        Line:
            rectangle: (self.x, self.y, self.width, self.height)
            width: dp(2)
        Color:
            rgba: 0,0,0,0
    color: 1,1,1,1
    font_size: '28sp'
    halign: 'center'
    valign: 'middle'
    text_size: self.size

<KeyBtn@RectBtn>:
    bg_color: 0.32,0.32,0.32,1
    border_color: 0,0,0,0

<ListItem@Button>:
    background_normal: ''
    background_color: 0.23,0.23,0.23,1
    color: 1,1,1,1
    markup: True
    font_size: '26sp'
    size_hint_y: None
    height: dp(52)
    text_size: self.width-dp(16), None
    halign: 'left'
    valign: 'middle'

<PassiveInput@TextInput>:
    readonly: True
    multiline: False
    cursor_blink: False
    cursor_width: 0
    use_bubble: False
    use_handles: False
    write_tab: False
    on_focus: self.focus = False
    on_double_tap: None
    on_triple_tap: None
    on_touch_down:
        (self.collide_point(*args[1].pos) and setattr(self, 'focus', False)) or False

<Root>:
    orientation: 'horizontal'
    padding: dp(12)
    spacing: dp(12)

    # ---------------- LEFT ----------------
    BoxLayout:
        id: left
        orientation: 'vertical'
        size_hint_x: 0.32
        spacing: dp(10)

        PassiveInput:
            id: search
            background_normal: ''
            background_active: ''
            background_color: 0.22,0.22,0.22,1
            foreground_color: 1,1,1,1
            font_size: '34sp'
            text: app.search_display
            halign: 'left'
            valign: 'middle'
            padding: [dp(18), dp(14), dp(18), dp(14)]
            size_hint_y: None
            height: dp(80)

        BoxLayout:
            orientation: 'vertical'
            spacing: dp(8)
            size_hint_y: 1
            canvas.before:
                Color:
                    rgba: 0.17,0.17,0.17,1
                Rectangle:
                    pos: self.pos
                    size: self.size
            padding: dp(6)
            RecycleView:
                id: rv
                key_viewclass: 'viewclass'
                key_size: 'height'
                viewclass: 'ListItem'
                RecycleBoxLayout:
                    default_size: None, dp(52)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: 'vertical'

        # E1–E5 unter der Liste
        GridLayout:
            id: e_row_left
            cols: 5
            size_hint_y: None
            height: dp(110)
            spacing: dp(6)
            RectBtn:
                id: zE1
                text: 'E-1'
                on_release: app.on_zone_press('E-1')
            RectBtn:
                id: zE2
                text: 'E-2'
                on_release: app.on_zone_press('E-2')
            RectBtn:
                id: zE3
                text: 'E-3'
                on_release: app.on_zone_press('E-3')
            RectBtn:
                id: zE4
                text: 'E-4'
                on_release: app.on_zone_press('E-4')
            RectBtn:
                id: zE5
                text: 'E-5'
                on_release: app.on_zone_press('E-5')

    # ---------------- MIDDLE ----------------
    BoxLayout:
        id: middle
        orientation: 'vertical'
        size_hint_x: 0.42
        spacing: dp(10)

        RectBtn:
            id: mode_btn
            text: app.mode_btn_text
            bg_color: app.mode_btn_color
            font_size: '40sp'
            size_hint_y: None
            height: dp(90)
            on_release: app.toggle_mode()

        Widget:
            size_hint_y: None
            height: dp(4)

        BoxLayout:
            orientation: 'vertical'
            spacing: dp(10)

            Label:
                id: zone_hint
                text: 'Zone wählen'
                color: 1,0.2,0.2,1
                font_size: '24sp'
                size_hint_y: None
                height: dp(28)
                opacity: 1 if app.mode=='booking' and not app.active_zone else 0

            RectBtn:
                id: zA
                text: 'A'
                on_release: app.on_zone_press('A')
            RectBtn:
                id: zB
                text: 'B'
                on_release: app.on_zone_press('B')
            RectBtn:
                id: zC
                text: 'C'
                on_release: app.on_zone_press('C')
            RectBtn:
                id: zD
                text: 'D'
                on_release: app.on_zone_press('D')

        # E6–E9 unter Zone D (gleiche Höhe wie A–D/E1–E5)
        GridLayout:
            id: e_row_mid
            cols: 4
            size_hint_y: None
            height: dp(110)
            spacing: dp(6)
            RectBtn:
                id: zE6
                text: 'E-6'
                on_release: app.on_zone_press('E-6')
            RectBtn:
                id: zE7
                text: 'E-7'
                on_release: app.on_zone_press('E-7')
            RectBtn:
                id: zE8
                text: 'E-8'
                on_release: app.on_zone_press('E-8')
            RectBtn:
                id: zE9
                text: 'E-9'
                on_release: app.on_zone_press('E-9')

    # ---------------- RIGHT (Keypad + F) ----------------
    BoxLayout:
        id: right
        orientation: 'vertical'
        size_hint_x: 0.26
        spacing: dp(10)

        BoxLayout:
            id: keyarea
            orientation: 'vertical'
            spacing: dp(10)
            size_hint_y: 1
            on_size: app.update_key_side(self)

            # Row 0: H + Backspace
            AnchorLayout:
                anchor_x: 'center'
                size_hint_y: None
                height: app.key_side
                BoxLayout:
                    orientation: 'horizontal'
                    spacing: dp(10)
                    size_hint_x: None
                    width: app.key_side*3 + dp(10)*2
                    KeyBtn:
                        text: 'H'
                        size_hint: None, None
                        size: app.key_side, app.key_side
                        on_release: app.keypad_char('H')
                    KeyBtn:
                        text: ''
                        size_hint: None, None
                        size: app.key_side*2 + dp(10), app.key_side
                        on_release: app.keypad_backspace()
                        Image:
                            source: 'backspace.png'
                            allow_stretch: True
                            keep_ratio: True
                            size_hint: None, None
                            height: min(self.parent.height*0.55, dp(44))
                            width: self.height * 3.886363636
                            x: self.parent.x + (self.parent.width - self.width)/2
                            y: self.parent.y + (self.parent.height - self.height)/2

            # Row 1: 7 8 9
            AnchorLayout:
                anchor_x: 'center'
                size_hint_y: None
                height: app.key_side
                BoxLayout:
                    orientation: 'horizontal'
                    spacing: dp(10)
                    size_hint_x: None
                    width: app.key_side*3 + dp(10)*2
                    KeyBtn:
                        text: '7'
                        size_hint: None, None
                        size: app.key_side, app.key_side
                        on_release: app.keypad_char('7')
                    KeyBtn:
                        text: '8'
                        size_hint: None, None
                        size: app.key_side, app.key_side
                        on_release: app.keypad_char('8')
                    KeyBtn:
                        text: '9'
                        size_hint: None, None
                        size: app.key_side, app.key_side
                        on_release: app.keypad_char('9')

            # Row 2: 4 5 6
            AnchorLayout:
                anchor_x: 'center'
                size_hint_y: None
                height: app.key_side
                BoxLayout:
                    orientation: 'horizontal'
                    spacing: dp(10)
                    size_hint_x: None
                    width: app.key_side*3 + dp(10)*2
                    KeyBtn:
                        text: '4'
                        size_hint: None, None
                        size: app.key_side, app.key_side
                        on_release: app.keypad_char('4')
                    KeyBtn:
                        text: '5'
                        size_hint: None, None
                        size: app.key_side, app.key_side
                        on_release: app.keypad_char('5')
                    KeyBtn:
                        text: '6'
                        size_hint: None, None
                        size: app.key_side, app.key_side
                        on_release: app.keypad_char('6')

            # Row 3: 1 2 3
            AnchorLayout:
                anchor_x: 'center'
                size_hint_y: None
                height: app.key_side
                BoxLayout:
                    orientation: 'horizontal'
                    spacing: dp(10)
                    size_hint_x: None
                    width: app.key_side*3 + dp(10)*2
                    KeyBtn:
                        text: '1'
                        size_hint: None, None
                        size: app.key_side, app.key_side
                        on_release: app.keypad_char('1')
                    KeyBtn:
                        text: '2'
                        size_hint: None, None
                        size: app.key_side, app.key_side
                        on_release: app.keypad_char('2')
                    KeyBtn:
                        text: '3'
                        size_hint: None, None
                        size: app.key_side, app.key_side
                        on_release: app.keypad_char('3')

            # Row 4: 0 + DEL
            AnchorLayout:
                anchor_x: 'center'
                size_hint_y: None
                height: app.key_side
                BoxLayout:
                    orientation: 'horizontal'
                    spacing: dp(10)
                    size_hint_x: None
                    width: app.key_side*3 + dp(10)*2
                    KeyBtn:
                        text: '0'
                        size_hint: None, None
                        size: app.key_side*2 + dp(10), app.key_side
                        on_release: app.keypad_char('0')
                    KeyBtn:
                        text: 'DEL'
                        size_hint: None, None
                        size: app.key_side, app.key_side
                        on_release: app.keypad_clear()

        RectBtn:
            id: zF
            text: 'F'
            on_release: app.on_zone_press('F')
            size_hint_y: None
            height: dp(110)
"""

class DataStore:
    def __init__(self, path=DB_FILE):
        # Thread-safe + Timeout für Blockaden vermeiden
        self.conn = sqlite3.connect(path, check_same_thread=False, timeout=2)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("CREATE TABLE IF NOT EXISTS pakete(id INTEGER PRIMARY KEY, code TEXT UNIQUE, zone TEXT, ts TEXT)")
        self.conn.commit()

    def upsert(self, code, zone):
        # ts nur beim ersten Insert setzen; spätere Zone-Änderung aktualisiert ts NICHT
        ts = datetime.utcnow().isoformat()
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO pakete(code, zone, ts) VALUES(?, ?, ?) "
            "ON CONFLICT(code) DO UPDATE SET zone=excluded.zone",
            (code, zone, ts),
        )
        self.conn.commit()

    def all(self):
        cur = self.conn.cursor()
        cur.execute("SELECT code, zone, ts FROM pakete ORDER BY code COLLATE NOCASE ASC")
        return cur.fetchall()

    def zone_of(self, code):
        cur = self.conn.cursor()
        cur.execute("SELECT zone FROM pakete WHERE code=?", (code,))
        r = cur.fetchone
        r = cur.fetchone()
        return r[0] if r else None

    def delete_older_than_days(self, days=10):
        limit = (datetime.utcnow() - timedelta(days=days)).isoformat()
        cur = self.conn.cursor()
        cur.execute("DELETE FROM pakete WHERE ts < ?", (limit,))
        self.conn.commit()

class Root(BoxLayout):
    pass

class HermesApp(App):
    mode = StringProperty("normal")
    search_text = StringProperty("")
    search_display = StringProperty("")
    packages = ListProperty([])
    active_zone = StringProperty("")
    selected_code = StringProperty("")
    scan_buffer = StringProperty("")
    db = ObjectProperty(None, rebind=True)
    mode_btn_text = StringProperty("EINBUCHEN")
    mode_btn_color = ListProperty([0.78,0.66,0.07,1])
    key_side = NumericProperty(dp(90))
    default_blue = ListProperty([0.11,0.46,0.78,1])

    # --- Zusatz: tägliche geplante Neustarts (22:10 & 05:30) ---
    def schedule_daily_restart(self):
        from datetime import datetime, timedelta

        def seconds_until(h, m):
            now = datetime.now()
            tgt = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if tgt <= now:
                tgt += timedelta(days=1)
            return (tgt - now).total_seconds()

        def do_restart(*_):
            try:
                sys.stdout.flush()
                sys.stderr.flush()
            except Exception:
                pass
            os._exit(0)

        # Zwei tägliche Trigger setzen
        Clock.schedule_once(lambda dt: Clock.schedule_once(lambda _dt: do_restart(), seconds_until(22, 10)), 0)
        Clock.schedule_once(lambda dt: Clock.schedule_once(lambda _dt: do_restart(), seconds_until(5, 30)), 0)

    def build(self):
        self.db = DataStore()
        Builder.load_string(KV)
        root = Root()
        Window.bind(on_key_down=self.on_key_down)
        Clock.schedule_once(self._post_build, 0)
        return root

    def _post_build(self, dt):
        # Display-Schlaf verhindern (falls X vorhanden)
        try:
            subprocess.Popen(["/usr/bin/xset", "s", "off"])
            subprocess.Popen(["/usr/bin/xset", "-dpms"])
            subprocess.Popen(["/usr/bin/xset", "s", "noblank"])
        except Exception:
            pass

        self.refresh_packages()
        self.update_search_display()
        self.db.delete_older_than_days(10)
        Clock.schedule_interval(lambda dt: self.safe_cleanup(), 3600)  # stündlich, safe

        # Auto-Update: alle 30 Minuten; offline-tolerant
        try:
            Clock.schedule_interval(lambda _dt: check_and_update_app_async(), 1800)
        except Exception as e:
            print("⚠️ Konnte Update-Scheduler nicht setzen:", e)

        # geplante tägliche Restarts
        self.schedule_daily_restart()

        self.update_all_zone_styles()

    def safe_cleanup(self):
        try:
            self.db.delete_older_than_days(10)
        except Exception as e:
            print("Cleanup failed:", e)

    def update_key_side(self, area):
        gap = dp(10)
        w = max(area.width, 1)
        h = max(area.height, 1)
        side_w = (w - gap*2) / 3.0
        side_h = (h - gap*4) / 5.0
        side = max(44, int(min(side_w, side_h)))
        self.key_side = side

    def refresh_packages(self):
        self.packages = self.db.all()
        self.apply_filter()

    def format_with_highlight(self, code, needle):
        if not needle:
            return code
        s = code.upper()
        n = needle.upper()
        i = s.find(n)
        if i == -1:
            return None
        return f"{code[:i]}[color=ffff00]{code[i:i+len(n)]}[/color]{code[i+len(n):]}"

    def apply_filter(self):
        rv = self.root.ids.rv
        needle = self.search_text
        data = []
        for code, zone, ts in self.packages:
            t = self.format_with_highlight(code, needle)
            if t is None:
                continue
            data.append({"text": t, "on_release": lambda c=code: self.on_item_select(c)})
        # Speicher-freundlich aktualisieren
        rv.data = []
        rv.data.extend(data)

    def on_item_select(self, code):
        self.selected_code = code
        self.update_all_zone_styles()

    def keypad_char(self, ch):
        self.selected_code = ""
        if self.mode == "normal":
            self.search_text += ch
            self.update_search_display()
            self.apply_filter()
        else:
            if not self.active_zone:
                return
            self.scan_buffer += ch
        self.update_all_zone_styles()

    def keypad_backspace(self):
        self.selected_code = ""
        if self.mode == "normal":
            if self.search_text:
                self.search_text = self.search_text[:-1]
                self.update_search_display()
                self.apply_filter()
        else:
            if self.scan_buffer:
                self.scan_buffer = self.scan_buffer[:-1]
        self.update_all_zone_styles()

    def keypad_clear(self):
        self.selected_code = ""
        if self.mode == "normal":
            self.search_text = ""
            self.update_search_display()
            self.apply_filter()
        else:
            self.scan_buffer = ""
        self.update_all_zone_styles()

    def update_search_display(self):
        self.search_display = self.search_text

    def toggle_mode(self):
        self.selected_code = ""
        if self.mode == "normal":
            self.mode = "booking"
            self.mode_btn_text = "FERTIG"
            self.mode_btn_color = [0.12,0.67,0.27,1]
            self.active_zone = ""
            self.scan_buffer = ""
        else:
            self.mode = "normal"
            self.mode_btn_text = "EINBUCHEN"
            self.mode_btn_color = [0.78,0.66,0.07,1]
            self.active_zone = ""
            self.scan_buffer = ""
        self.update_search_display()
        self.update_all_zone_styles()

    def on_zone_press(self, zone):
        if self.mode == "booking":
            self.active_zone = zone
            self.update_all_zone_styles()

    def commit_scan_buffer(self):
        code = self.scan_buffer.strip()
        if not code:
            return
        self.db.upsert(code, self.active_zone)

        # --- B2-Backup nach Einbuchen (asynchron, offline-tolerant) ---
        backup_db_async()

        self.scan_buffer = ""
        self.refresh_packages()
        self.update_all_zone_styles()

    def on_key_down(self, window, key, scancode, codepoint, modifier):
        # Backspace
        if key in (8,):
            self.keypad_backspace()
            return True

        # Delete
        if key in (127,):
            self.keypad_clear()
            return True

        # Alle gängigen Scan-Ende-Tasten: Enter, Tab, Space, LineFeed
        if key in (9, 10, 13, 271, 32):
            if self.mode == "booking" and self.active_zone:
                self.commit_scan_buffer()
            return True

        # Alphanumerische Zeichen erfassen
        if codepoint:
            c = codepoint.upper()
            if c.isalnum():
                self.keypad_char(c)
                return True

        return False

    def update_all_zone_styles(self):
        ids = self.root.ids
        mapping = {
            "A":"zA","B":"zB","C":"zC","D":"zD",
            "E-1":"zE1","E-2":"zE2","E-3":"zE3","E-4":"zE4","E-5":"zE5",
            "E-6":"zE6","E-7":"zE7","E-8":"zE8","E-9":"zE9",
            "F":"zF"
        }
        selected_zone = None
        if self.mode == "normal" and self.selected_code:
            cur = self.db.conn.cursor()
            cur.execute("SELECT zone FROM pakete WHERE code=?", (self.selected_code,))
            r = cur.fetchone()
            selected_zone = r[0] if r else None

        for z, wid_id in mapping.items():
            w = ids.get(wid_id)
            if not w:
                continue
            if self.mode == "booking":
                if self.active_zone == z:
                    w.bg_color = (1,1,0,1)   # gelb
                    w.color    = (0,0,0,1)   # schwarzer Text
                else:
                    w.bg_color = (0,0,0,1)   # schwarz
                    w.color    = (1,1,1,1)
            else:
                if selected_zone == z:
                    w.bg_color = (1,0,0,1)   # rot bei Treffer im Suchmodus
                else:
                    w.bg_color = tuple(self.default_blue)
                w.color = (1,1,1,1)

class Root(BoxLayout):
    pass

if __name__ == "__main__":
    HermesApp().run()
