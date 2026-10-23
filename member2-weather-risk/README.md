# member2-weather-risk

> **ChhayaRakshak AI — Member 2: Weather & Risk Assessment**
> Isolated development module. Pilot area: **Hyderabad, India**.

---

## ⚠️ Temporary development module

This folder is Member 2's **isolated workspace**. It contains a standalone
FastAPI application developed and tested independently from the rest of the
team's code.

**It will be integrated into the shared application
(`ai-intelligence-backend/main.py`) once:**

1. The shared database schema is finalised with **Member 4**.
2. The router API contracts are reviewed by the team.

**Do not:**
- Modify any files under `frontend/` or `ai-intelligence-backend/`.
- Create shared database models here before Member 4 coordination.
- Duplicate Member 3's image-analysis or chat modules.

---

## Implemented endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/health` | Service health check |
| `GET`  | `/api/weather?lat=&lon=` | Current weather observation (Open-Meteo) |
| `POST` | `/api/assessments` | Deterministic heat-risk assessment |

### GET /api/weather

Fetches real current weather from [Open-Meteo](https://open-meteo.com/) (no API key required).
Returns temperature, apparent temperature, relative humidity, wind speed,
weather code (WMO), observation time, timezone, units, and data-quality notes.

- Returns `400` for invalid coordinates.
- Returns `503` when the upstream API is unavailable.
- **Never fabricates weather values.**

### POST /api/assessments

Accepts field observation data, fetches live weather, and computes a deterministic
heat-risk score (0–100) with explainable factors and mitigation recommendations.

Request body fields (all optional except `latitude`/`longitude`):

| Field | Type | Description |
|-------|------|-------------|
| `latitude` | float | **Required.** Survey latitude (°N) |
| `longitude` | float | **Required.** Survey longitude (°E) |
| `location_name` | string | Human-readable location name |
| `area_type` | string | Area type / land use |
| `surface_type` | string | Primary ground surface material |
| `shade_availability` | string | Visible shade availability category |
| `canopy_density` | int 0–100 | Observed tree canopy density (%) |
| `footfall` | string | Pedestrian exposure / footfall category |
| `demographics` | list[str] | Observed vulnerable demographic groups |
| `hydration_present` | bool | Free hydration within 50 m |
| `notes` | string | Field surveyor notes |

Response fields include: `assessment_id`, `location`, `risk_score`,
`risk_category`, `temperature`, `humidity`, `model_version`, `model_valid`,
`model_limitations`, `factors`, `recommendations`.

#### Risk categories

| Score | Category |
|-------|----------|
| 0–24  | `low` |
| 25–49 | `moderate` |
| 50–74 | `high` |
| 75–100 | `very_high` |

**The score is an indicative decision-support measure, not a medically validated prediction.**

---

## Folder structure

```
member2-weather-risk/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Isolated FastAPI entry point (dev only)
│   ├── db/
│   │   ├── __init__.py
│   │   └── persistence.py       # Persistence stub — awaiting Member 4 integration
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── weather.py           # GET /api/weather
│   │   └── assessments.py       # POST /api/assessments
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── weather_schemas.py   # WeatherResponse, WeatherErrorResponse
│   │   └── risk_schemas.py      # AssessmentRequest, AssessmentResponse, etc.
│   └── services/
│       ├── __init__.py
│       ├── weather_service.py   # Open-Meteo HTTP client
│       └── risk_service.py      # Deterministic scoring engine
├── tests/
│   ├── __init__.py
│   ├── test_health.py
│   ├── test_weather_service.py
│   ├── test_weather_route.py
│   ├── test_risk_service.py
│   └── test_assessment_route.py
├── pytest.ini
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup

### Prerequisites

- Python 3.10 or newer

### 1. Create a virtual environment

```bash
cd member2-weather-risk
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env`.  No changes are required to run with Open-Meteo (no API key needed).
Do **not** set `DATABASE_URL` until Member 4 integration is agreed.

> **Never commit `.env` to version control.**

---

## Running the isolated dev server

```bash
# Run from inside member2-weather-risk/
uvicorn app.main:app --reload --port 8001
```

- Swagger UI: http://127.0.0.1:8001/docs
- Health check: http://127.0.0.1:8001/api/health
- Weather: http://127.0.0.1:8001/api/weather?lat=17.385&lon=78.487

Runs on port **8001** to avoid conflicting with `ai-intelligence-backend` on port 8000.

---

## Running tests

```bash
# Run from inside member2-weather-risk/
python -m pytest tests/ -v
```

Tests are fully isolated — no live API calls or database connections required.

---

## Scoring model documentation

See the module docstring in [`app/services/risk_service.py`](app/services/risk_service.py)
for the full scoring method, sub-score weights, boundaries, and limitations.

---

## Database integration plan

Assessment persistence is currently a **stub** (`app/db/persistence.py`).
When Member 4's shared database schema and SQLAlchemy session are ready:

1. Replace `save_assessment_stub` with an async implementation that maps
   `AssessmentResponse` to Member 4's ORM model.
2. Set `DATABASE_URL` in `.env` (format: `mysql+aiomysql://user:pass@host/db`).
3. Never hardcode credentials.

---

## Integration into the shared backend

When ready, add to `ai-intelligence-backend/main.py`:

```python
from app.routes.weather     import router as weather_router
from app.routes.assessments import router as assessments_router

app.include_router(weather_router)
app.include_router(assessments_router)
```

All routers use the `/api` prefix (team convention).

---

## Coordination checklist (before integration)

- [ ] Review and merge `requirements.txt` additions into the shared file
- [ ] Coordinate shared database models with Member 4
- [ ] Replace `app/db/persistence.py` stub with real persistence
- [ ] Review router prefix and schema naming with Member 3 to avoid conflicts
- [ ] Update `ai-intelligence-backend/README.md` with new endpoint documentation
