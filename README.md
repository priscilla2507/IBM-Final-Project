<<<<<<< HEAD
# ChhayaRakshak AI

AI-powered urban heat protection and cooling intervention planning platform.
Pilot area: **Hyderabad, India**.

---

## Project structure

```
ChhayaRakshak-AI/
├── ai-intelligence-backend/       # AI backend module (Member 3)
│   ├── app/
│   │   ├── config.py              # Settings loaded from environment variables
│   │   ├── schemas/
│   │   │   └── ai_schemas.py      # Pydantic request/response models
│   │   ├── services/
│   │   │   └── gemini_service.py  # Gemini API calls (vision + chat)
│   │   └── routes/
│   │       ├── image_analysis.py  # POST /api/analyze-image
│   │       └── chat.py            # POST /api/chat
│   ├── tests/
│   │   ├── test_gemini_service.py # Unit tests (service layer, mocked)
│   │   ├── test_image_analysis.py # Route tests (image endpoint, mocked)
│   │   └── test_chat.py           # Route tests (chat endpoint, mocked)
│   ├── main.py                    # FastAPI application entry point
│   ├── requirements.txt
│   └── .env.example               # Copy to .env and fill in values
├── README.md
└── .gitignore                     # .env (any depth) is already ignored
```

---

## Setup

### 1. Prerequisites

- Python 3.10 or newer
- A Google Gemini API key — obtain one from https://aistudio.google.com/app/apikey
- A supported Gemini model name — check https://ai.google.dev/gemini-api/docs/models

### 2. Clone the repository

```bash
git clone https://github.com/YOUR_ORG/ChhayaRakshak-AI.git
cd ChhayaRakshak-AI/ai-intelligence-backend
```

### 3. Create a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 4. Install dependencies

```bash
# Run from inside ai-intelligence-backend/
pip install -r requirements.txt
```

### 5. Configure environment variables

Copy the example file and fill in your values:

```bash
# Run from inside ai-intelligence-backend/
cp .env.example .env
```

Open `.env` and set:

```dotenv
GEMINI_API_KEY=<your Google Gemini API key>
GEMINI_MODEL=<model name, e.g. gemini-2.0-flash>
MAX_IMAGE_SIZE_MB=10
```

> **Never commit `.env` to version control.**
> It is already listed in `.gitignore`.

---

## Running the backend

```bash
# Run from inside ai-intelligence-backend/
uvicorn main:app --reload
```

The server starts at `http://127.0.0.1:8000` by default.

- Swagger UI (interactive docs): http://127.0.0.1:8000/docs
- ReDoc:                          http://127.0.0.1:8000/redoc
- OpenAPI schema (JSON):          http://127.0.0.1:8000/openapi.json
- Health check:                   http://127.0.0.1:8000/health

---

## API endpoints

### `POST /api/analyze-image`

Upload a JPG or PNG image of an outdoor public space. Returns a structured
analysis of visible shade, vegetation, shelters, and infrastructure gaps.

**Request:** `multipart/form-data`

| Field | Type   | Description                        |
|-------|--------|------------------------------------|
| file  | file   | JPG or PNG image, max 10 MB        |

**Response (200):**

```json
{
  "success": true,
  "data": {
    "vegetation":        { "visible": true,  "description": "Several trees visible along the footpath." },
    "shaded_areas":      { "visible": true,  "description": "Shade cast by trees covers the left pavement." },
    "sun_exposed_areas": { "visible": true,  "description": "Central carriageway fully exposed to sun." },
    "shelters":          { "visible": false, "description": null },
    "drinking_water":    { "visible": false, "description": null },
    "infrastructure_gaps": [
      "No covered bus shelter visible",
      "No drinking water point visible"
    ],
    "explanation": "The image shows a tree-lined street with partial shade on the pavement. The road surface and central area are fully sun-exposed with no visible shade infrastructure.",
    "limitations": "Cannot confirm whether drinking water or shelter facilities exist off-frame or around the corner. Image angle may obscure some infrastructure.",
    "human_verification_required": true
  },
  "error": null
}
```

**Error responses:**

| Status | Cause                                      |
|--------|--------------------------------------------|
| 413    | File exceeds 10 MB limit                   |
| 415    | Unsupported file type or renamed non-image |
| 422    | No file uploaded, or file is empty         |
| 503    | Gemini configuration missing or API error  |
| 500    | Unexpected server error                    |

---

### `POST /api/chat`

Ask the multilingual heat-safety assistant a question. Answers are grounded
in reviewed public-health guidance (WHO, ICMR, NDMA) and are for general
awareness only — not medical advice.

**Request:** `application/json`

```json
{
  "question": "What should I do if I feel dizzy in the heat?",
  "language": "english"
}
```

| Field    | Type   | Values                          | Default   |
|----------|--------|---------------------------------|-----------|
| question | string | 1–1000 characters               | required  |
| language | string | `english` · `hindi` · `telugu`  | `english` |

**Response (200):**

```json
{
  "success": true,
  "answer": "If you feel dizzy in the heat, move to a cool or shaded area immediately. Sit or lie down to prevent falling. Drink cool water in small sips if you are conscious and able to swallow. Loosen tight clothing. If dizziness does not improve within a few minutes, or if you also have nausea, confusion, or very hot skin, seek medical assistance immediately.",
  "language_code": "english",
  "disclaimer": "This information is for general awareness only. It is not medical advice. For emergencies, seek urgent medical assistance immediately.",
  "error": null
}
```

**Error responses:**

| Status | Cause                                          |
|--------|------------------------------------------------|
| 422    | Empty question, question too long, invalid language, or config missing |
| 503    | Gemini API unavailable                         |
| 500    | Unexpected server error                        |

---

## Testing with Swagger UI

1. Start the server (from inside `ai-intelligence-backend/`): `uvicorn main:app --reload`
2. Open http://127.0.0.1:8000/docs in your browser.

### Test `POST /api/analyze-image`

1. Click **POST /api/analyze-image** → **Try it out**.
2. Under **file**, click **Choose File** and select a JPG or PNG photo of a
   street, bus stop, market, or footpath.
3. Click **Execute**.
4. Inspect the structured JSON response under **Server response**.

### Test `POST /api/chat`

1. Click **POST /api/chat** → **Try it out**.
2. Edit the request body:
   ```json
   {
     "question": "How can I protect myself from heatstroke?",
     "language": "english"
   }
   ```
3. To test Hindi, change `"language"` to `"hindi"` and write the question in
   Hindi or English — Gemini will respond in Hindi either way.
4. To test Telugu, use `"telugu"`.
5. Click **Execute** and read the answer and disclaimer in the response.

---

## Running the automated tests

Tests are fully mocked — they do not require a configured API key or internet access.

```bash
# Run from inside ai-intelligence-backend/
python -m pytest tests/ -v
```

Expected result: **53 tests pass, 0 failures, 0 warnings**.

| Test file                      | Coverage                                      |
|--------------------------------|-----------------------------------------------|
| `tests/test_gemini_service.py` | Service functions, JSON parsing, error cases  |
| `tests/test_image_analysis.py` | Image route: validation, MIME, errors, schema |
| `tests/test_chat.py`           | Chat route: languages, validation, errors     |

---

## Integration with other team modules

`main.py` contains commented-out placeholder imports for the other teams'
routers. When the weather/risk, map, and optimisation modules are ready,
register them in `main.py`:

```python
# from app.routes.weather import router as weather_router
# app.include_router(weather_router)
```

All routers must use the `/api` prefix to keep paths consistent.

---

## Security notes

- `GEMINI_API_KEY` is loaded from `.env` only and is never logged or returned
  in any API response.
- Uploaded image bytes are held in memory only for the duration of the request
  and are not stored on disk.
- File type is validated using magic bytes (not just the file extension) to
  reject renamed non-image files.
- All AI findings from image analysis are marked
  `"human_verification_required": true` and must not be used as the sole
  basis for infrastructure decisions.
- The chat assistant is explicitly instructed not to diagnose individuals, not
  to invent medical facts, and to direct users to emergency services for
  serious symptoms.
=======
# IBM-PROJECT
>>>>>>> 42c579d388fa8111fdf0ffe413a45b0d9c871058
