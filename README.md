# Hermes Paket Einlagerungssystem

Ein Touchscreen-optimiertes System zur **Verwaltung und Einlagerung von Hermes-Paketen** mit Barcode-Scanner und physischer Tastatureingabe.  
Entwickelt für eine Auflösung von **1200 × 800 Pixeln (Vollbild)**, lauffähig unter Windows und Debian / Raspberry Pi.

---

## 🧩 Funktionsübersicht

### Hauptmodi
#### 🔍 Normalmodus
- Startet automatisch beim Programmstart.  
- Suchfeld oben links zeigt eingegebene oder gescannte Sendungsnummern.  
- Die Liste darunter filtert **live** nach der Eingabe.  
  - Übereinstimmende Zeichen werden **gelb hervorgehoben**.  
  - Nur passende Sendungen bleiben sichtbar.  
- Wird eine Sendungsnummer ausgewählt:
  - Die zugehörige **Zone leuchtet rot**.
  - Alle anderen Zonen erscheinen blau.
- Eingaben erfolgen ausschließlich über den physischen oder den eingebauten **Nummernblock**.  
  Keine Bildschirmtastatur.

#### 📦 Einbuchenmodus
- Aktivierung über den **„Einbuchen“-Button** (oben Mitte).  
- UI ändert sich:
  - Die Zonenbuttons A–F (E 1–E 4) sind aktiv.
  - Nicht ausgewählte Zonen: **schwarz**.
  - Ausgewählte Zone: **gelb mit schwarzer Schrift**.
- Nach Auswahl einer Zone können Pakete **per Barcode-Scanner** gescannt werden.
  - Der Scanner sendet die Nummer + *Carriage Return (`\r`)*.
  - Der Eintrag wird direkt in die Datenbank übernommen (`pakete.db`).
  - Zone, Datum und Uhrzeit der **ersten Einlagerung** werden gespeichert.
  - Eine Sendung kann immer **nur einer Zone** zugeordnet sein.  
    Wird sie erneut eingebucht, wird **nur die Zone geändert**, nicht der Zeitstempel.
- Mit **„Fertig“** kehrt die App in den Normalmodus zurück.

---

## 💾 Datenbankstruktur (`pakete.db`)

| Spalte | Typ | Beschreibung |
|--------|-----|---------------|
| `id` | INTEGER PRIMARY KEY | Automatische ID |
| `code` | TEXT UNIQUE | Sendungsnummer (z. B. `H390111024124`) |
| `zone` | TEXT | Aktuelle Lagerzone (z. B. `E-3`) |
| `ts` | TEXT (ISO 8601) | Zeitstempel des ersten Einlagerungsscans |

- Alte Einträge (> 10 Tage) werden automatisch gelöscht.  
- `code` ist **eindeutig** – ein Paket existiert nur einmal.

---

## 🎛 Steuerung

### Eingabequellen
- **Barcode-Scanner** (sendet `code + CR`).
- **Nummernblock** auf Touchscreen (virtuell).
- **PC-Tastatur** (gleiche Steuerlogik):
  - **0–9, H** – Zeichen eingeben  
  - **Backspace** – letztes Zeichen löschen  
  - **DEL** – Feld leeren  
  - **Enter** – Scan abschließen  
  - **Modus-Taste** – zwischen Normal und Einbuchen wechseln  

### Bedienlogik
- Alle Eingaben über Tasten oder Scanner.
- Kein Fokuswechsel mit der Maus.
- Suchfeld ist **passiv** (keine Bildschirmtastatur).

---

## 🖥 Installation

### Windows
```bash
python -m venv .venv
.venv\Scripts\activate
pip install kivy==2.3.0 kivy_deps.sdl2 kivy_deps.glew kivy_deps.angle
