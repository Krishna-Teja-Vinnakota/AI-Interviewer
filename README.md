# AI Interviewer

An AI-powered platform that automates first-level recruitment: resume screening, candidate invitations, live AI video interviews, and scored evaluation reports.

Built with **FastAPI**, **MongoDB**, **Google Vertex AI (Gemini 2.5 Pro)**, **Deepgram**, and **Bunny CDN**.

---

## Prerequisites

- **Python** 3.10+
- **MongoDB Atlas** account (cloud-hosted MongoDB)
- **Modern browser** (Chrome / Edge — for `MediaRecorder` and `getUserMedia`)

You also need accounts and credentials for these external services:

| Service | Used For | What you need |
|---|---|---|
| **MongoDB Atlas** | Primary database + GridFS for PDFs | Atlas connection URI |
| **Google Cloud (Vertex AI + TTS)** | Gemini screening, embeddings, question audio | Service account JSON, project ID |
| **Deepgram** | Real-time speech-to-text | API key |
| **Bunny CDN** | Interview video storage | Storage zone, password, hostname |
| **SMTP** (e.g. Gmail) | Sending invitation emails (**mandatory**) | Host, user, app password |

---

## Setup

```powershell
# 1. Clone and enter the project
git clone <repository-url> ai-interviewer
cd ai-interviewer

# 2. Create a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1     # Windows
# source .venv/bin/activate      # macOS / Linux

# 3. Install dependencies
cd backend
pip install -r requirements.txt

# 4. Place your GCP service account JSON in backend/
#    e.g. backend/Client-Service-Account.json

# 5. Create backend/.env (see below)
```

### `backend/.env`

```env
# MongoDB Atlas
MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/
MONGODB_DATABASE_NAME=ai_interviewer

# Google Vertex AI
VERTEX_AI_SERVICE_ACCOUNT_PATH=./Client-Service-Account.json
VERTEX_AI_PROJECT_ID=your-gcp-project-id
VERTEX_AI_LOCATION=us-central1

# Google TTS (reuses the Vertex AI key)
GOOGLE_TTS_CREDENTIALS_PATH=./Client-Service-Account.json

# Deepgram
DEEPGRAM_API_KEY=your_deepgram_api_key

# Bunny CDN
BUNNY_STORAGE_ZONE=your-storage-zone
BUNNY_API_KEY=your-bunny-storage-password
BUNNY_CDN_HOSTNAME=your-zone.b-cdn.net
BUNNY_STORAGE_REGION=de

# SMTP (required)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your.email@example.com
SMTP_PASSWORD=your_app_password
SMTP_TLS=True

# App
BASE_URL=http://localhost:8000
TIMEZONE=Asia/Kolkata
```

> SMTP is **mandatory** — invitations fail and roll back if email cannot be sent.

---

## How to Get the Credentials

### MongoDB Atlas

1. Sign up at [cloud.mongodb.com](https://cloud.mongodb.com/) and create a free **M0 cluster**.
2. In **Database Access**, create a database user with a username and password.
3. In **Network Access**, add your IP (or `0.0.0.0/0` for development).
4. Click **Connect → Drivers** on your cluster and copy the connection string. It looks like:
   ```
   mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
5. Put it in `.env`:
   ```env
   MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/
   MONGODB_DATABASE_NAME=ai_interviewer
   ```

The database and all collections are created automatically on first use.

---

### Deepgram

1. Sign up at [console.deepgram.com](https://console.deepgram.com/) (free tier includes generous STT credits).
2. From the dashboard sidebar, click **API Keys → Create a New API Key**.
3. Give it a name (e.g. `ai-interviewer`), select scope **Member** (or restrict to `Speech-to-Text`), and click **Create Key**.
4. Copy the key shown **once** and put it in `.env`:
   ```env
   DEEPGRAM_API_KEY=your_deepgram_api_key
   ```

> The frontend fetches this key at runtime via `/api/config/deepgram-key` for the live STT WebSocket.

---

### Bunny CDN

1. Sign up at [bunny.net](https://bunny.net/) and verify your account.
2. Go to **Storage** in the sidebar → **Add Storage Zone**.
   - Pick a **zone name** (e.g. `ai-interviewer-videos`) → this becomes `BUNNY_STORAGE_ZONE`.
   - Pick a **main storage region** — `DE` (Germany), `NY`, `LA`, or `SG` → this becomes `BUNNY_STORAGE_REGION` (lowercase, e.g. `de`).
3. Open the new storage zone → **FTP & API Access** tab.
   - Copy the **Password** value → this becomes `BUNNY_API_KEY` (Bunny uses the storage password as the API key for uploads).
4. Still in the storage zone, go to **Connected Pull Zones → Connect Pull Zone** (or create a new one).
   - Note the pull zone hostname, e.g. `ai-interviewer.b-cdn.net` → this becomes `BUNNY_CDN_HOSTNAME`.
5. Put everything in `.env`:
   ```env
   BUNNY_STORAGE_ZONE=ai-interviewer-videos
   BUNNY_API_KEY=your-bunny-storage-password
   BUNNY_CDN_HOSTNAME=ai-interviewer.b-cdn.net
   BUNNY_STORAGE_REGION=de
   ```

> Interview recordings are uploaded as `interviews/{interview_id}/complete.webm` and served from the pull zone.

---

### SMTP (Email — Gmail recommended)

SMTP is **required** — the app sends interview invitation codes via email and rolls back the invitation if delivery fails.

**Using Gmail (recommended for development):**

1. Use a Gmail account dedicated to this app.
2. Enable **2-Step Verification** at [myaccount.google.com/security](https://myaccount.google.com/security).
3. Generate an **App Password** at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords):
   - App: **Mail**, Device: **Other** → name it `ai-interviewer`.
   - Copy the 16-character password Google shows (spaces can be removed).
4. Put the values in `.env`:
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your.email@gmail.com
   SMTP_PASSWORD=your_16_char_app_password
   SMTP_TLS=True
   ```

**Using another SMTP provider** (SendGrid, Mailgun, Office 365, corporate relay, etc.):
- `SMTP_HOST` → provider's SMTP server hostname
- `SMTP_PORT` → `587` for STARTTLS (most common) or `465` for SSL
- `SMTP_USER` / `SMTP_PASSWORD` → the credentials issued by the provider
- `SMTP_TLS=True` for STARTTLS on port 587

> The "From" address used in invitation emails is `SMTP_USER`. Make sure your provider allows sending from that address.

---

## Run

```powershell
cd backend
python run.py
```

The server starts on `http://localhost:8000` and opens a browser tab automatically.

| URL | Page |
|---|---|
| `/` | Landing page |
| `/recruiter.html` | Recruiter dashboard |
| `/candidate.html` | Candidate invitation entry |
| `/docs` | Swagger API docs |

---

## Database

MongoDB collections and GridFS buckets are created automatically on first write — no manual schema setup required.

**Collections:** `resumes`, `candidates`, `job_descriptions`, `screening_results`, `interview_invitations`, `interviews`, `answers`, `analysis_results`, plus `fs.files` / `fs.chunks` (GridFS for resume PDFs).

---

## Workflow

1. Recruiter creates a **Job Description**.
2. Recruiter uploads **resumes** — Gemini screens each against the JD.
3. Recruiter clicks **Proceed** on shortlisted candidates → email with invitation code is sent.
4. Candidate enters the code and starts a **live AI interview** (camera, mic, TTS questions, Deepgram STT, proctoring).
5. Recording uploads to Bunny CDN; Gemini generates a scored **evaluation report**.

---

## Project Structure

```
ai-interviewer/
├── backend/
│   ├── main.py                       # FastAPI app entry point
│   ├── run.py                        # Dev server launcher
│   ├── requirements.txt              # Python dependencies
│   ├── .env                          # Environment variables (git-ignored)
│   ├── Client-Service-Account.json    # GCP service account key (git-ignored)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── dependencies.py           # FastAPI dependency helpers
│   │   └── routes.py                 # All HTTP route definitions
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                 # pydantic-settings configuration
│   │   ├── database.py               # MongoDB + GridFS connection
│   │   ├── models.py                 # Pydantic document models
│   │   └── schemas.py                # Request / response schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py             # Vertex AI / Gemini / TTS
│   │   ├── analysis_service.py       # Post-interview scoring
│   │   ├── bunny_service.py          # Bunny CDN video upload
│   │   ├── email_service.py          # SMTP invitation emails
│   │   ├── interview_service.py      # Interview session lifecycle
│   │   ├── jd_service.py             # Job description CRUD
│   │   └── resume_service.py         # Resume parsing & screening
│   └── utils/
│       ├── __init__.py
│       └── timezone.py               # IST timezone helpers
├── frontend/
│   ├── index.html                    # Landing page
│   ├── recruiter.html                # Recruiter dashboard
│   ├── candidate.html                # Candidate invitation entry
│   ├── interview.html                # Live interview UI
│   ├── css/
│   │   ├── styles.css                # Global / landing styles
│   │   ├── recruiter.css
│   │   ├── candidate.css
│   │   └── interview.css
│   └── js/
│       ├── main.js                   # Shared entry script
│       ├── utils.js                  # API helpers, toasts
│       ├── recruiter.js              # Recruiter dashboard logic
│       ├── candidate.js              # Candidate flow
│       ├── interview.js              # Live interview logic
│       ├── deepgram-stt.js           # Deepgram WebSocket client
│       └── proctoring.js             # Tab-switch / focus monitor
├── face-verification-test.html       # Standalone face-verification test page
├── test.py                           # Ad-hoc test script
├── .gitignore
└── README.md
```

API documentation is available live at `http://localhost:8000/docs` (Swagger) and `/redoc` once the server is running.

---

## Notes

- `.env`, the GCP service account JSON, and all `__pycache__` folders are git-ignored — never commit them.
- The app has no built-in auth — add a layer (OAuth2/SSO/IP allow-list) before production exposure.
- CORS is open (`*`) in dev; restrict it in [backend/main.py](backend/main.py) for production.
- HTTPS is required for camera/microphone access on any non-localhost domain.
