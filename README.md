# Service Booking & Management API (FastAPI + MongoDB)

High-performance, production-ready RESTful backend built with **FastAPI**, **MongoDB Atlas**, and **Google Gemini AI Integration** for the cross-platform Service Booking & Management Mobile Application.

---

## 🌟 Key Architecture & Security Features

- **Framework**: FastAPI (Asynchronous Python 3.12)
- **Database**: MongoDB Atlas via `motor` (Async non-blocking I/O)
- **Security Standards**:
  - **OWASP Recommended Security Headers**: Strict CSP, `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN`, and server disclosure stripping (`Server`, `X-Powered-By`).
  - **Sliding-Window Rate Limiting**: In-memory thread-safe rate limiter with automated memory cleanup preventing DoS attacks.
  - **Brute Force & Credential Stuffing Defense**: Account-level and IP-level locking with sliding evaluation window.
  - **Character Encoding Integrity (`Utf8JSONResponse`)**: Explicit `charset=utf-8` JSON responses ensuring Dart/Flutter HTTP clients never experience Latin1 character corruption (Mojibake).
  - **Cryptographic Password Security**: PBKDF2-HMAC-SHA256 with 32-byte cryptographic salt and constant-time digest verification.
  - **Stateless JWT Authentication**: Access tokens and persistent session management.
- **AI Integration**:
  - AI Service Assistant powered by Google Gemini API with system-level context injection of live service catalog and intelligent fallback engine.
  - Zero API key exposure to mobile clients (backend proxy architecture).

---

## 📁 Folder Structure

```
service_booking_management_app_backend/
├── app/
│   ├── core/
│   │   ├── brute_force.py      # Anti-brute force and lockout manager
│   │   ├── config.py           # Environment and settings loader
│   │   ├── database.py         # Async Motor client & MongoDB indexes
│   │   ├── deps.py             # JWT auth & route dependencies
│   │   ├── rate_limit.py       # Sliding-window rate limiter middleware
│   │   ├── responses.py        # Utf8JSONResponse and standard response helpers
│   │   └── security.py         # PBKDF2 hashing & JWT creation/verification
│   ├── modules/
│   │   ├── ai_assistant/       # AI Service Assistant module
│   │   ├── appointments/       # Booking & conflict-prevention engine
│   │   ├── auth/               # Customer register, login, session
│   │   ├── services/           # Service catalog, search & filtering
│   │   └── users/              # User profile management
│   ├── utils/
│   │   └── helpers.py          # BSON ObjectId and serialization utilities
│   └── main.py                 # FastAPI application factory & middleware setup
├── scripts/
│   ├── run_server.py           # Server runner entrypoint
│   ├── seed_data.py            # Database seeder with sample services and demo user
│   └── test_api.py             # Automated API test suite
├── .env                        # Configuration file
├── requirements.txt            # Python dependencies
└── README.md
```

---

## 🚀 Setup & Execution

### 1. Prerequisites
- Python 3.11+ or 3.12+
- Active MongoDB connection (MongoDB Atlas URI or local instance)

### 2. Environment Configuration
Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```
Ensure your MongoDB URL and Gemini API Key are set:
```env
MONGODB_URL=mongodb+srv://<username>:<password>@servicebookingdb.czvmevv.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=servicebookingdb
JWT_SECRET=your_jwt_secret_key
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Install Dependencies
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Seed Database
Populate initial services and a demo customer account (`testuser@example.com` / `password123`):
```bash
python scripts/seed_data.py
```

### 5. Run Automated Tests
```bash
python scripts/test_api.py
```

### 6. Start the Server
```bash
python scripts/run_server.py
```
Or directly with Uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive API documentation will be available at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

## 📡 API Endpoints Overview

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/auth/register` | Register new customer | No |
| `POST` | `/api/auth/login` | Login with email & password | No |
| `GET` | `/api/auth/me` | Get current user profile | Yes (Bearer) |
| `POST` | `/api/auth/logout` | Terminate session | Yes (Bearer) |
| `GET` | `/api/users/profile` | View profile details | Yes (Bearer) |
| `PUT` | `/api/users/profile` | Update profile information | Yes (Bearer) |
| `POST` | `/api/users/change-password` | Change account password | Yes (Bearer) |
| `GET` | `/api/services` | List all services (search & filter) | No |
| `GET` | `/api/services/featured` | List featured/popular services | No |
| `GET` | `/api/services/categories` | Get all service categories | No |
| `GET` | `/api/services/{id}` | Get individual service details | No |
| `GET` | `/api/appointments/availability` | Check slot availability for date | No |
| `POST` | `/api/appointments` | Book new appointment | Yes (Bearer) |
| `GET` | `/api/appointments/my` | View user's appointments | Yes (Bearer) |
| `GET` | `/api/appointments/{id}` | View single appointment details | Yes (Bearer) |
| `PATCH` | `/api/appointments/{id}/cancel` | Cancel an appointment | Yes (Bearer) |
| `POST` | `/api/ai/chat` | Chat with AI Service Assistant | No / Optional |
| `GET` | `/api/ai/prompts` | Get starter prompts for AI assistant | No |
