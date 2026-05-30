# 🛡️ DriveLegal AI — Intelligent Road Safety Legal Assistant

> **IIT Madras Road Safety Hackathon 2026** — AI-powered chatbot for traffic laws, violations, and penalties with **global coverage**

![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1+-green?logo=flask)
![Gemini](https://img.shields.io/badge/Gemini_2.0-AI_Powered-blueviolet?logo=google)
![Countries](https://img.shields.io/badge/Countries-7-orange)
![PWA](https://img.shields.io/badge/PWA-Offline_Ready-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Setup & Installation](#-setup--installation)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Database Structure](#-database-structure)
- [Offline Functionality](#-offline-functionality)
- [Global Coverage](#-global-coverage)
- [Geo-Fencing](#-geo-fencing)
- [Mobile & Responsive Design](#-mobile--responsive-design)
- [Team & Work Division](#-team--work-division)
- [Evaluation Criteria Mapping](#-evaluation-criteria-mapping)

---

## 🎯 Overview

**DriveLegal AI** is an AI-powered legal chatbot that provides **location-specific information** on traffic laws, violations, fines, and enforcement procedures **across 7 countries**. It integrates national rules with **state and local enforcement regulations** to help citizens easily understand traffic regulations, calculate challans, and promote road safety.

### Problem Statement
Citizens often lack easy access to clear, location-specific information about traffic laws, penalties, and enforcement procedures. Fine structures vary significantly across states and countries, creating confusion. DriveLegal AI solves this by providing a centralized, AI-powered platform with **global applicability**.

### Key Highlights
- 🌍 **7 Countries**: India, USA, UK, UAE, Germany, Australia, Canada
- 🇮🇳 **India Deep Coverage**: 28 states + 3 UTs, 26+ violations, 64+ city mappings
- 📍 **GPS Geo-Fencing**: Auto-detects your state from GPS location
- ⚡ **Full Offline Mode**: Calculator works without internet using cached data
- 🤖 **Gemini 2.0 AI**: Intelligent chat with offline rule-based fallback

---

## ✨ Key Features

### 1. 🧠 AI-Powered Chat Interface
- **Gemini 2.0 Flash** for intelligent, context-aware responses
- 10-pattern offline fallback engine (helmet, seatbelt, speeding, drunk driving, etc.)
- Domain-restricted — only answers road safety / traffic law queries
- Multi-session support with conversation history
- Voice input via Web Speech API

### 2. 📍 Geo-Fenced Fine Lookup
- **Automatic GPS detection** via Geolocation API + Nominatim reverse geocoding
- City-to-state mapping for **64+ Indian cities**
- Auto-selects user's state in the calculator
- Server-side geo API endpoints (`/api/geo/state`, `/api/geo/detect`)
- Coverage for all **28 states and 3 union territories**

### 3. 💰 Challan / Fine Calculator
- **26+ Indian violations** with MV Act section references
- **6 international countries** with local violation data
- Calculates fines based on:
  - Violation type
  - Vehicle type (bike, car, truck, bus, auto, taxi — with weight modifiers)
  - Location (state-specific overrides for India)
  - First offense vs repeat offense
- **Cross-state comparison** — compare fines across all 34 states/UTs
- Fine breakdown with applicable law section, additional penalties, and safety advice
- **Offline calculator fallback** — computes fines locally from cached JSON when API is down

### 4. 🌍 Global Applicability
- **India**: 26 violations, 28 states + 3 UTs, Motor Vehicles Amendment Act 2019
- **USA**: DUI, speeding, seatbelt, phone use, red light, no insurance ($)
- **UK**: Drink driving, speeding, phone use, penalty points (£)
- **UAE**: Zero-tolerance DUI, black points system (AED)
- **Germany**: Flensburg points, Autobahn rules (€)
- **Australia**: Demerit points, phone detection cameras (A$)
- **Canada**: Criminal Code impaired driving, provincial laws (C$)
- Country-specific emergency numbers, BAC limits, speed units, and drive-side info

### 5. ⚡ Offline Functionality & Robustness
- **Service Worker (PWA)** caches:
  - All static assets (HTML, CSS, JS)
  - All JSON data files (`india_national.json`, `india_states.json`, `global_rules.json`, `translations.json`)
  - API responses (`/api/violations`, `/api/states`, `/api/countries`)
- **Network-first strategy** with cache fallback for all API calls
- **Client-side calculator** mirrors backend logic for offline fine computation
- **Offline badge** appears automatically when connection is lost
- **Pre-loads all JSON data** at startup for instant offline access

### 6. 🎨 User Interface & Accessibility
- **Premium dark mode** with orange accent design system
- **Light mode** toggle with theme persistence
- **6 language support**: English, Hindi, Telugu, Tamil, Kannada, Bengali
- **Responsive design**:
  - Desktop (>1024px): Full sidebar + content
  - Tablet (769-1024px): Compact sidebar
  - Mobile (≤768px): Drawer navigation, optimized touch targets
  - Small phones (≤380px): Compact layout
  - iOS notch support via `env(safe-area-inset-bottom)`
- **Voice input** via Web Speech API
- **Keyboard accessible** navigation
- **Print styles** for calculator results

### 7. 🛡️ Safety & Emergency Features
- **SOS Emergency Button** — shares GPS location via Web Share API
- National helplines: Police (112), Ambulance (108), Highway Rescue (1033)
- Community hazard reporting with map markers
- Safety score dashboard with progress ring
- Every violation response includes safety advice and "why this law exists" context

### 8. 👤 User System
- **JWT authentication** with registration and login
- Chat history persistence per user
- Safety score tracking
- Community hazard reporting with upvotes

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     FRONTEND (PWA)                       │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────────┐ │
│  │ Chat UI  │  │ Geolocation│  │ Service Worker       │ │
│  │ + Voice  │  │ + Reverse  │  │ (Offline Cache)      │ │
│  │ + i18n   │  │   Geocode  │  │ + Offline Calculator │ │
│  └────┬─────┘  └─────┬──────┘  └──────────┬───────────┘ │
│       └───────────────┼───────────────────┘              │
│                       │ REST API                         │
├───────────────────────┼──────────────────────────────────┤
│                    BACKEND (Flask)                        │
│  ┌──────────┐  ┌──────┴─────┐  ┌────────────────────┐   │
│  │ Flask    │  │ NLP Engine │  │ Challan Calculator  │   │
│  │ Server   │──│ (Gemini 2  │──│ (Vehicle modifiers, │   │
│  │ + Auth   │  │  + Offline │  │  state overrides)   │   │
│  │ + JWT    │  │  fallback) │  │                     │   │
│  └──────────┘  └──────┬─────┘  └─────────┬───────────┘  │
│                       │                   │               │
│              ┌────────┴───────────────────┴────────┐      │
│              │        Rules Database               │      │
│              │   (Structured JSON + SQLite)        │      │
│              └────────────────────────────────────┘      │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  📁 data/                                          │  │
│  │  ├── india_national.json  (MV Act 2019 — 26 viol) │  │
│  │  ├── india_states.json    (28 states + 3 UTs)     │  │
│  │  ├── global_rules.json    (6 countries)           │  │
│  │  └── translations.json    (6 languages)           │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
hackaton/
├── app.py                    # Flask server — 18 API routes, auth, geo-fencing
├── nlp_engine.py             # Gemini 2.0 AI + offline rule-based fallback
├── challan_calculator.py     # Fine engine — vehicle modifiers, state overrides
├── rules_database.py         # JSON loader — national, state, and global rules
├── wsgi.py                   # Production WSGI entry point
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── .env                      # Local environment config (not in git)
├── README.md                 # This file
│
├── data/                     # Structured rules database (served via /data/ route)
│   ├── india_national.json   # Motor Vehicles Act 2019 — 26 violations
│   ├── india_states.json     # 28 states + 3 UTs, 64 city mappings
│   ├── global_rules.json     # 6 countries: USA, UK, UAE, Germany, Australia, Canada
│   └── translations.json     # UI strings in 6 Indian languages
│
└── static/                   # Frontend assets (PWA)
    ├── index.html            # Main SPA — chat, calculator, map, dashboard, SOS
    ├── styles.css            # Design system — dark/light theme, responsive
    ├── app.js                # Client logic — offline calc, geo-fencing, voice
    ├── sw.js                 # Service worker — caches assets, data, and APIs
    └── manifest.json         # PWA manifest for install-to-homescreen
```

---

## 🚀 Setup & Installation

### Prerequisites
- **Python 3.8+** installed
- **pip** package manager

### Steps

```bash
# 1. Clone or navigate to the project directory
cd hackaton

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. (Optional) Set up Gemini AI — get key from https://aistudio.google.com/app/apikey
# Copy .env.example to .env and add your GEMINI_API_KEY
# If no key is provided, the app runs in offline fallback mode

# 4. Run the server
python app.py

# 5. Open in browser
# Visit http://localhost:5000
```

The app starts at `http://localhost:5000`. AI works in **offline fallback mode** without a Gemini API key — all features except AI chat work fully.

### Quick Test
After starting the server, try these:
- **Chat**: "Fine for no helmet in Mumbai" → Returns Maharashtra-specific fine
- **Chat**: "DUI fine in USA vs India" → Cross-country comparison
- **Chat**: "Traffic rules in UAE Dubai" → UAE-specific data
- **Calculator**: Select country → violations → vehicle → Calculate
- **Offline**: Toggle DevTools offline → Calculator still works

---

## 📡 API Documentation

### Core Endpoints

#### `GET /api/health`
Server health check.
```json
{"status": "ok", "version": "1.0.0", "db_loaded": true, "ai_ready": false}
```

#### `POST /api/chat`
Main chat endpoint. Processes natural language queries with Gemini 2.0 or offline fallback.

**Request:**
```json
{
  "message": "Fine for no helmet in Delhi",
  "session_id": "unique_session_id"
}
```

**Response:**
```json
{
  "text": "Driving without a helmet is a violation of Section 194D...",
  "data": {"type": "ai_response", "source": "gemini-2.0"},
  "confidence": "High",
  "latency_ms": 450
}
```

---

### Calculator Endpoints

#### `POST /api/calculate` (India)
Calculate fine for Indian violations with state overrides and vehicle modifiers.

**Request:**
```json
{
  "violations": ["no_helmet", "drunk_driving"],
  "vehicle_type": "car",
  "state": "maharashtra",
  "is_repeat": false
}
```

**Response:**
```json
{
  "violations": [
    {
      "violation_key": "no_helmet",
      "violation_name": "Riding without Helmet",
      "section": "194D",
      "national_fine": 1000,
      "state_fine": 500,
      "state_label": "Maharashtra",
      "vehicle_type": "car",
      "vehicle_modifier": 1.0,
      "total_fine": 500,
      "imprisonment": null
    }
  ],
  "grand_total": 10500,
  "count": 2,
  "vehicle_type": "car",
  "state": "maharashtra"
}
```

#### `POST /api/calculate/global` (International)
Calculate fines for international violations.

**Request:**
```json
{
  "violations": ["speeding", "drunk_driving"],
  "country": "usa",
  "is_repeat": false
}
```

**Response:**
```json
{
  "violations": [...],
  "grand_total": 2150,
  "country": "United States",
  "currency": "$"
}
```

#### `GET /api/compare?violation=no_helmet&vehicle_type=two_wheeler`
Compare a violation's fine across all 34 Indian states/UTs.

---

### Data Endpoints

#### `GET /api/violations`
List all Indian violation types (26 violations).

#### `GET /api/violations?country=uk`
List violations for a specific country.

#### `GET /api/states`
List all 33 Indian states and UTs with display names.

#### `GET /api/countries`
List all 6 supported countries.

#### `GET /api/country/<country_key>`
Full data for a country (violations, emergency numbers, BAC limit, speed units).

#### `GET /data/<filename>`
Serve raw JSON data files for offline caching (used by service worker).

---

### Geo-Fencing Endpoints

#### `GET /api/geo/state?city=mumbai`
Map a city name to its state for geo-fenced fine lookup.

**Response:**
```json
{
  "city": "mumbai",
  "state_key": "maharashtra",
  "state_name": "Maharashtra"
}
```

#### `GET /api/geo/detect`
Returns the full city-to-state mapping (64 entries) for client-side geo-fencing.

---

### Auth & Community Endpoints

#### `POST /api/auth/register` / `POST /api/auth/login`
JWT-based user authentication.

#### `GET /api/user/dashboard`
User dashboard with safety score, query count, and report count. Requires JWT token.

#### `GET/POST /api/hazards`
Community hazard reporting — submit and retrieve map-based safety hazards.

---

## 🗄️ Database Structure

### National Rules (`india_national.json`)
- **26 violation types** with MV Act sections
- Fine amounts for first and repeat offenses
- Vehicle-type-specific fines (e.g., overspeeding varies by vehicle)
- Additional penalties (imprisonment, licence suspension, vehicle impoundment)
- Safety advice, law explanations, and repeat consequences
- Speed limits for city/highway/expressway by vehicle type
- Emergency numbers and required documents

### State Rules (`india_states.json`)
- **28 states and 3 union territories** with individual override profiles
- State-specific fine overrides (e.g., West Bengal has lower fines, Delhi has strict enforcement)
- Local enforcement rules and notable information
- **64 city-to-state mappings** for geo-aware responses

### Global Rules (`global_rules.json`)
- **6 countries**: USA, UK, UAE, Germany, Australia, Canada
- Per-country: currency, drive side, speed unit, BAC limit, emergency number, legal driving age
- 4-6 violations per country with first/repeat offense fines and additional penalties

### Translations (`translations.json`)
- UI strings in **6 languages**: English, Hindi, Telugu, Tamil, Kannada, Bengali

---

## ⚡ Offline Functionality

DriveLegal AI is designed to work in **low-network and no-network conditions**:

### Service Worker (PWA)
- Caches all static assets on install
- Caches all 4 JSON data files (`india_national.json`, `india_states.json`, `global_rules.json`, `translations.json`)
- Pre-caches API responses (`/api/violations`, `/api/states`, `/api/countries`)
- **Network-first strategy**: Tries API first, falls back to cache
- Returns structured offline JSON when completely disconnected

### Client-Side Calculator
When the server is unreachable, the frontend automatically:
1. Loads cached JSON data from the service worker
2. Computes fines locally using the same algorithm as `challan_calculator.py`
3. Applies vehicle modifiers and state overrides
4. Displays results with an **"⚡ Offline Estimate"** badge
5. Works for both India and all 6 international countries

### Offline UI Indicators
- **Offline badge** appears in the header when `navigator.onLine` is false
- Auto-hides when connection is restored
- Chat shows offline mode message when API fails

---

## 🌍 Global Coverage

| Country | Currency | Violations | Drive Side | Emergency | BAC Limit |
|---------|----------|-----------|------------|-----------|-----------|
| 🇮🇳 India | ₹ (INR) | 26 | Left | 112 | 0.03% |
| 🇺🇸 USA | $ (USD) | 6 | Right | 911 | 0.08% |
| 🇬🇧 UK | £ (GBP) | 6 | Left | 999 | 0.08% |
| 🇦🇪 UAE | AED | 5 | Right | 999 | 0% (Zero) |
| 🇩🇪 Germany | € (EUR) | 5 | Right | 112 | 0.05% |
| 🇦🇺 Australia | A$ (AUD) | 5 | Left | 000 | 0.05% |
| 🇨🇦 Canada | C$ (CAD) | 3 | Right | 911 | 0.08% |

---

## 📍 Geo-Fencing

DriveLegal AI auto-detects the user's location for geo-fenced fine lookup:

1. **GPS Detection**: Uses browser Geolocation API to get lat/lng
2. **Reverse Geocoding**: Calls Nominatim (OpenStreetMap) to get city name — free, no API key
3. **City-to-State Mapping**: Matches city against 64+ Indian city mappings
4. **Auto-Selection**: Pre-selects the detected state in the calculator dropdown
5. **Toast Notification**: Shows "📍 Detected: Maharashtra" confirmation

The geo-fencing works entirely client-side with no paid API dependencies.

---

## 📱 Mobile & Responsive Design

| Breakpoint | Layout | Optimizations |
|-----------|--------|--------------|
| **Desktop** (>1024px) | Full sidebar + content | Standard layout |
| **Tablet** (769-1024px) | Compact sidebar (220px) | Full-width calculator |
| **Mobile** (≤768px) | Drawer navigation | Smaller buttons, stacked forms, compact grid |
| **Small phone** (≤380px) | 2-column stats grid | Smaller fonts and chips |
| **iOS (notched)** | Safe area insets | Bottom padding for input area |

Additional:
- Touch-optimized button sizes (minimum 42px)
- Print stylesheet for calculator results
- `100dvh` viewport height for mobile browsers

---

## 👥 Team & Work Division

### Core Team (8 Members)

| Member | Role | Responsibilities | Files Owned |
| :---: | :--- | :--- | :--- |
| **nischal202006** | **Backend Lead & DevOps** | Flask architecture, SQLite schema, JWT Auth, API endpoints, geo-fencing API | `app.py`, `wsgi.py` |
| **hemanthkumar2006** | **AI / NLP Engineer** | Gemini 2.0 integration, prompt engineering, global context detection | `nlp_engine.py` |
| **vineelsaireddy** | **Frontend Lead (UI/UX)** | CSS/Design system, dark/light theme, responsive breakpoints, PWA | `static/styles.css`, `static/index.html` |
| **Jittu496** | **Location Systems Engineer**| Leaflet Map, hotspots, geo-fencing auto-detect, reverse geocoding | `static/app.js` (map + geo logic) |
| **Shashank3312** | **Core Logic Engineer** | Challan calculator, state override logic, offline calculator, vehicle modifiers | `challan_calculator.py` |
| **RiyasShaik** | **Data & Localization Lead** | JSON legal datasets, state mapping, global rules, i18n translations | `data/*.json`, `rules_database.py` |
| **Chervith-Reddy**| **Safety & Features Dev** | Emergency SOS UI, Dashboard, Safety score, community hazards | `static/index.html` (panels) |
| **Kowshikh-10** | **Integration & QA** | Testing, E2E bug fixes, README, frontend API wireup, offline fallback | `README.md`, `static/app.js` |

### 12-Day Development Sprint Timeline (May 1 - May 12, 2026)

| Phase | Days | Focus | Commits Made |
|-------|------|-------|--------------| 
| **Phase 1: Foundation** | May 1 - 3 | Project structure, Flask, NLP drafts, UI scaffolding, national database | ~10 commits |
| **Phase 2: Core Features** | May 4 - 7 | API endpoints, chat interface, fine calculations, state-level data, SOS | ~9 commits |
| **Phase 3: Integrations** | May 8 - 10 | DB optimization, PWA implementation, offline fallback, map hotspots | ~8 commits |
| **Phase 4: Polish & QA** | May 11 - 12 | E2E testing, WSGI/SSL setup, Gemini prompt refinement, UI responsiveness | ~8 commits |
| **Phase 5: Global & Geo** | May 28 - 29 | Global rules (6 countries), geo-fencing, offline calculator, data serving fix | ~5 commits |

---

## 📊 Evaluation Criteria Mapping

| Criteria | Score | Evidence |
|----------|-------|---------|
| **Legal accuracy & regulatory coverage** | ✅ High | 26 violations from MV Act 2019 with exact sections, first/repeat offense fines, additional penalties, imprisonment terms | 
| **Challan calculator functionality & correctness** | ✅ High | Vehicle modifiers (0.75x-1.5x), state overrides for 33 regions, repeat offense doubling, per-extra-passenger/tonne surcharges, offline fallback |
| **Information integration across countries** | ✅ High | 7 countries (India + USA, UK, UAE, Germany, Australia, Canada), country-specific currencies, emergency numbers, BAC limits, drive-side info |
| **User interface & accessibility** | ✅ High | Premium dark/light theme, 6 languages, voice input, responsive (mobile/tablet/desktop/notch), PWA installable, offline indicator |

### Key Differentiators
- 🌐 **Geo-fencing** — GPS + Nominatim auto-detects state, no paid APIs
- ⚡ **Full offline calculator** — Computes fines client-side from cached JSON, mirrors backend logic exactly
- 🔄 **Dual AI** — Gemini 2.0 online + 10-pattern rule-based offline fallback
- 📱 **PWA** — Install to homescreen, works like native app
- 🌍 **7 countries** — Not just India, global traffic law coverage
- 📊 **State comparison** — Compare fines across all 34 Indian states/UTs for any violation

---

## 📜 License

This project is built for the **IIT Madras Road Safety Hackathon 2026** organized by the Centre of Excellence for Road Safety (CoERS), RBG Labs.

---

## 🙏 Acknowledgments

- **Motor Vehicles (Amendment) Act, 2019** — Ministry of Road Transport and Highways, Government of India
- **Parivahan Sewa** — parivahan.gov.in
- **IIT Madras CoERS** — For organizing this hackathon
- **OpenStreetMap Nominatim** — For free reverse geocoding API
- **Google Gemini 2.0** — For AI-powered conversational engine

---

> **"Every response we generate has the potential to save a life on the road."**
> — DriveLegal AI Team
