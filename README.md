# Service Booking & Management API (FastAPI + MongoDB)

High-performance, production-ready RESTful backend built with **FastAPI**, **MongoDB Atlas**, and **Google Gemini AI Integration** for the cross-platform Service Booking & Management Mobile Application.

---

## 🌟 Key Architecture & Security Features

- **Framework**: FastAPI (Asynchronous Python 3.11+ / 3.12+)
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
  - Multi-session chat support with conversation history storage and clearing.
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
│   │   ├── ai_assistant/       # AI Service Assistant & sessions module
│   │   ├── appointments/       # Booking & conflict-prevention engine
│   │   ├── auth/               # Customer & provider register, login, session
│   │   ├── notifications/      # Real-time notifications & badge counts
│   │   ├── ratings/            # Ratings & feedback (Submit, Edit, Delete)
│   │   ├── services/           # Service catalog, search, filter & provider CRUD
│   │   └── users/              # User & provider profile management
│   ├── utils/
│   │   └── helpers.py          # BSON ObjectId and serialization utilities
│   └── main.py                 # FastAPI application factory & middleware setup
├── scripts/
│   ├── run_server.py           # Server runner entrypoint
│   ├── seed_data.py            # Database seeder with sample services and demo users
│   └── test_api.py             # Automated API verification test suite
├── .env                        # Configuration file
├── requirements.txt            # Python dependencies
└── README.md
```

---

## 🚀 Setup & Execution

### 1. Prerequisites
- Python 3.11+ or 3.12+
- Active MongoDB connection (MongoDB Atlas URI or local instance)
- Google Gemini API Key

### 2. Environment Configuration
Create a `.env` file in the root backend directory using the provided template:
```bash
cp .env.example .env
```
Update `.env` with your actual MongoDB connection URI, JWT secret, and optional Gemini API key. Refer to `.env.example` for details.

### 3. Install Dependencies
```bash
python -m venv .venv

# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Seed Database
Populate initial services catalog and demo accounts for both customer and service provider:
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

## 🔑 Demo Accounts

| Role | Email | Password |
|------|-------|----------|
| **Customer** | `testuser@example.com` | `password123` |
| **Service Provider** | `provider@example.com` | `password123` |

---

## 📡 API Endpoints Overview

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/auth/register` | Register new customer or provider | No |
| `POST` | `/api/auth/login` | Login with email & password | No |
| `GET` | `/api/auth/me` | Get current user identity & role | Yes (Bearer) |
| `POST` | `/api/auth/logout` | Terminate session | Yes (Bearer) |
| `GET` | `/api/users/profile` | View profile details | Yes (Bearer) |
| `PUT` | `/api/users/profile` | Update profile information | Yes (Bearer) |
| `POST` | `/api/users/change-password` | Change account password | Yes (Bearer) |
| `GET` | `/api/services` | List all services (search, category, sort) | No |
| `GET` | `/api/services/featured` | List featured/HOT services | No |
| `GET` | `/api/services/categories` | Get all distinct service categories | No |
| `GET` | `/api/services/{id}` | Get individual service details | No |
| `GET` | `/api/services/provider/my-services` | Provider: List own services with search & filter | Yes (Provider) |
| `POST` | `/api/services` | Provider: Create new service | Yes (Provider) |
| `PUT` | `/api/services/{id}` | Provider: Update service & sync appointments | Yes (Provider) |
| `DELETE` | `/api/services/{id}` | Provider: Delete service | Yes (Provider) |
| `GET` | `/api/appointments/availability` | Check slot availability for date | No |
| `POST` | `/api/appointments` | Book new appointment | Yes (Bearer) |
| `GET` | `/api/appointments/my` | View customer appointments | Yes (Bearer) |
| `GET` | `/api/appointments/{id}` | View single appointment details | Yes (Bearer) |
| `PATCH` | `/api/appointments/{id}/cancel` | Cancel an appointment | Yes (Bearer) |
| `GET` | `/api/appointments/provider/my-bookings` | Provider: View assigned bookings | Yes (Provider) |
| `PATCH` | `/api/appointments/{id}/status` | Provider: Update appointment status | Yes (Provider) |
| `GET` | `/api/ratings/service/{service_id}` | Get reviews for a service | No |
| `POST` | `/api/ratings` | Submit review for completed appointment | Yes (Bearer) |
| `PUT` | `/api/ratings/{id}` | Edit submitted review & recalculate score | Yes (Bearer) |
| `DELETE` | `/api/ratings/{id}` | Delete review & update stats | Yes (Bearer) |
| `GET` | `/api/notifications` | Get notifications history | Yes (Bearer) |
| `GET` | `/api/notifications/unread-count` | Get unread notifications count | Yes (Bearer) |
| `PATCH` | `/api/notifications/{id}/read` | Mark single notification as read | Yes (Bearer) |
| `PATCH` | `/api/notifications/read-all` | Mark all notifications as read | Yes (Bearer) |
| `DELETE` | `/api/notifications/{id}` | Delete notification | Yes (Bearer) |
| `POST` | `/api/ai/chat` | Chat with AI Service Assistant | No / Optional |
| `GET` | `/api/ai/prompts` | Get starter prompts for AI assistant | No |
| `GET` | `/api/ai/sessions` | List user's AI chat sessions | Yes (Bearer) |
| `GET` | `/api/ai/sessions/{id}` | Get messages for a session | Yes (Bearer) |
| `DELETE` | `/api/ai/sessions/{id}` | Delete single AI session | Yes (Bearer) |
| `DELETE` | `/api/ai/sessions` | Clear all AI sessions | Yes (Bearer) |
