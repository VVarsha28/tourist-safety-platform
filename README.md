# SafeTrail — Tourist Safety & Regional Command Platform

## 🌐 Live Deployed Application

- **Live URL**: **[https://tourist-safety-platform.onrender.com](https://tourist-safety-platform.onrender.com)**
- **Sign In / Demo Hub**: **[https://tourist-safety-platform.onrender.com/login](https://tourist-safety-platform.onrender.com/login)**
- **Sample Public QR Verification Pass**: **[Verify Elena's Digital Pass](https://tourist-safety-platform.onrender.com/verify/ST-2026-ESP-4109)**

> [!TIP]
> **1-Click Demo Profiles**: On the sign-in page, click any of the 4 quick-switch buttons (Authority HQ, Elena, Carlos, Aarav) for instant zero-password testing!

---

## ⚡ Demo Accounts & Roles

| Role / Profile | Email | Password | Scenario / Status |
| :--- | :--- | :--- | :--- |
| **Authority Command** | `authority@safetrail.gov` | `admin123` | Desktop operations center with live map, active SOS dispatch, and triage |
| **Elena Rostova** | `elena@demo.com` | `tourist123` | Situated in **Johari Bazaar Caution Zone** — fires live geofence warning & AI score |
| **Carlos Mendez** | `carlos@demo.com` | `tourist123` | Has an **Active SOS Emergency** beacon tracking live on the command map |
| **Aarav Sharma** | `aarav@demo.com` | `tourist123` | Situated in **City Palace Safe Heritage Zone** with high 90+ safety score |

---

## 🌟 Key Features

### 1. Tourist Mobile Web App (`/tourist/`)
- **Safety Profile & Snapshot**: Full passport details (masked in UI), blood group, allergies, pre-existing conditions, emergency contacts, and travel itinerary.
- **Digital Tourist ID & Live QR Verification**:
  - Official security pass with photo, unique ID code (e.g. `ST-2026-ESP-4109`), validity dates, and masked passport number (`****4109`).
  - High-contrast QR code pointing to public read-only verification page (`/verify/<tourist_id>`).
  - Full-screen view toggle and print/download button.
- **Location-Based Safety & Interactive Leaflet Map**:
  - Live GPS tracking and demo Location Simulator (switch instantly between Safe, Caution, and Restricted zones).
  - Geofence zone overlays: Safe Heritage Corridor (Green), Caution Market Sector (Amber), Restricted Mountain Pass (Red).
  - Safety POIs: Hospitals, Police stations, and Embassies with directions and phone numbers.
- **Emergency SOS with 3-Second Countdown**:
  - Floating red SOS button accessible from any screen.
  - 3-second abortable countdown ring to prevent accidental triggers.
  - Automatically captures GPS coordinates and dispatches medical vitals snapshot to Regional Command.
  - Live 4-step status tracker: `Triggered` ➔ `Acknowledged` ➔ `Dispatched` ➔ `Resolved`.
  - Voice/text notes for live responder guidance.
  - Simulated SMS dispatch to emergency contact.
- **AI Risk-Scoring Engine (0–100)**:
  - Deterministic multi-factor scoring function: zone danger rating, time-of-day cutoff (9 PM curfew), local incident density, and itinerary check.
  - Traffic-light indicator badge on tourist home.
- **AI Safety Assistant (Chatbot)**:
  - Contextual offline knowledge assistant answering queries about nearest hospitals, police stations, lost passport protocols, taxi scam precautions, and zone safety.
- **Non-Emergency Incident Reporting**:
  - File reports for theft, scams, harassment, lost items, or hazards with auto-GPS tagging and anonymous option.
  - "My Reports" real-time status tracker (`submitted` ➔ `under_review` ➔ `resolved`).
- **Safety Resources**:
  - Toll-free helplines (112, 1363, 108, 1091), safety dos and don'ts, common scams guide, and emergency checklist.

### 2. Authority Operations Dashboard (`/authority/dashboard`)
- **Live Regional Surveillance Map**:
  - Leaflet command map with all tourist locations (color-coded by AI safety rating).
  - High-visibility pulsing red beacon for active SOS emergencies.
  - Zone boundary polygons and emergency POIs.
- **Active SOS Console**:
  - Priority distress queue with audible alert siren on new triggers.
  - Single-click inspection of tourist medical snapshot (blood group, allergies, pre-existing conditions, emergency contact).
  - Dispatch workflow controls: `Acknowledge` ➔ `Dispatch Squad` ➔ `Resolve`.
- **Incident Triage Queue**:
  - Filterable by status (`all`, `submitted`, `under_review`, `resolved`) and category.
  - Direct status update and authority notes logging.
- **Tourist ID Lookup & Verification**:
  - Real-time search by Digital Tourist ID code or name with full unmasked authorized dossier.
- **Analytics Panel (Chart.js)**:
  - Incidents by Category (Doughnut chart).
  - Incident Density by City Zone (Bar chart).

---

## 🚀 Local Development

### Prerequisites
- Python 3.10+ (tested on Python 3.12)

### 1. Install Dependencies
```bash
py -3.12 -m pip install -r requirements.txt
```

### 2. Seed Database with Jaipur Demo City
```bash
py -3.12 seed.py
```
This seeds:
- 3 City Zones (Safe, Caution, Restricted)
- 5 Safety POIs (Hospitals, Police HQ, Consular Liaison)
- 1 Authority Command user (`authority@safetrail.gov` / `admin123`)
- 3 Preloaded Tourist accounts (Elena, Carlos, Aarav)
- Pre-populated incidents in triage queue

### 3. Run Locally
```bash
py -3.12 app.py
```
Open **`http://127.0.0.1:5000`** in your browser.

---

## 🧪 Automated Test Suite
Run the full test suite with:
```bash
py -3.12 test_app.py
```
Outputs 8 passing unit & integration tests covering telemetry, geofencing, SOS lifecycle, QR verification, and AI assistant.
