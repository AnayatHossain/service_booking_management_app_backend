# Service Booking & Management System — REST API Specification

- **Base URL (Local)**: `http://localhost:8000/api`
- **Base URL (Android Emulator)**: `http://10.0.2.2:8000/api`
- **Specification Format**: OpenAPI 3.0 / FastAPI Swagger
- **Authentication**: Stateless Bearer JWT (`Authorization: Bearer <token>`)
- **Payload Format**: `application/json; charset=utf-8`

---

## 📑 Summary of Endpoints

| Group | Method | Endpoint | Description | Auth |
|---|---|---|---|---|
| **Auth** | `POST` | `/auth/register` | Register new Customer or Provider | Public |
| | `POST` | `/auth/login` | Login and receive Bearer JWT | Public |
| | `GET` | `/auth/me` | Fetch authenticated user data | Bearer |
| | `POST` | `/auth/logout` | Terminate session | Bearer |
| **Users** | `GET` | `/users/profile` | View profile details | Bearer |
| | `PUT` | `/users/profile` | Update profile (name, phone, institution) | Bearer |
| | `POST` | `/users/change-password` | Update account password | Bearer |
| **Services** | `GET` | `/services` | List all services (search, category, sort) | Public |
| | `GET` | `/services/featured` | List HOT / Featured services | Public |
| | `GET` | `/services/categories` | List distinct service categories | Public |
| | `GET` | `/services/{id}` | Retrieve individual service details | Public |
| **Provider** | `GET` | `/services/provider/my-services` | Provider: View own services (with search) | Provider |
| | `POST` | `/services` | Provider: Add new service | Provider |
| | `PUT` | `/services/{id}` | Provider: Update service & sync appointments | Provider |
| | `DELETE`| `/services/{id}` | Provider: Delete service | Provider |
| **Bookings** | `GET` | `/appointments/availability` | Check time slots availability for date | Public |
| | `POST` | `/appointments` | Create new appointment booking | Bearer |
| | `GET` | `/appointments/my` | View client's bookings list | Bearer |
| | `GET` | `/appointments/{id}` | View single appointment details | Bearer |
| | `PATCH`| `/appointments/{id}/cancel` | Cancel an appointment | Bearer |
| | `GET` | `/appointments/provider/my-bookings` | Provider: View assigned bookings | Provider |
| | `PATCH`| `/appointments/{id}/status` | Provider: Update appointment status | Provider |
| **Ratings** | `GET` | `/ratings/service/{service_id}` | Fetch reviews for a specific service | Public |
| | `POST` | `/ratings` | Submit review for completed appointment | Bearer |
| | `PUT` | `/ratings/{id}` | Edit rating score and feedback comment | Bearer |
| | `DELETE`| `/ratings/{id}` | Delete rating & recalculate stats | Bearer |
| **Notifications** | `GET` | `/notifications` | List user notification history | Bearer |
| | `GET` | `/notifications/unread-count` | Retrieve unread counter (supports 99+) | Bearer |
| | `PATCH`| `/notifications/{id}/read` | Mark single notification as read | Bearer |
| | `PATCH`| `/notifications/read-all` | Mark all notifications as read | Bearer |
| | `DELETE`| `/notifications/{id}` | Delete notification | Bearer |
| **AI Assistant** | `POST` | `/ai/chat` | Conversational query with Gemini AI | Optional |
| | `GET` | `/ai/prompts` | Get quick suggestion prompt chips | Public |
| | `GET` | `/ai/sessions` | List user's conversation sessions | Bearer |
| | `GET` | `/ai/sessions/{id}` | Get messages for specific session | Bearer |
| | `DELETE`| `/ai/sessions/{id}` | Delete conversation session | Bearer |
| | `DELETE`| `/ai/sessions` | Clear all AI conversation history | Bearer |

---

## 🔑 Endpoint Details & Examples

### 1. Authentication

#### `POST /api/auth/login`
- **Request Body**:
```json
{
  "email": "testuser@example.com",
  "password": "password123"
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": "67389a1b4f...",
      "name": "Alex Johnson",
      "email": "testuser@example.com",
      "role": "customer",
      "avatar_url": "https://api.dicebear.com/7.x/initials/svg?seed=AlexJohnson"
    }
  }
}
```

---

### 2. Services Catalog

#### `GET /api/services`
- **Query Parameters**:
  - `search` (string, optional): Search by name, description, or category.
  - `category` (string, optional): Filter by category (e.g. `Home Cleaning`).
  - `sort_by` (string, optional): `price_asc`, `price_desc`, `rating_desc`.
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": [
    {
      "id": "67389b2c...",
      "name": "Full House Deep Cleaning",
      "category": "Home Cleaning",
      "price": 120.0,
      "duration_minutes": 180,
      "image_url": "https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&w=800&q=80",
      "is_featured": true,
      "rating": 4.9,
      "total_reviews": 128
    }
  ]
}
```

---

### 3. Appointments & Booking

#### `POST /api/appointments`
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
```json
{
  "service_id": "67389b2c...",
  "date": "2026-11-25",
  "time_slot": "10:00 AM",
  "customer_notes": "Please ring front doorbell upon arrival."
}
```
- **Response `201 Created`**:
```json
{
  "success": true,
  "message": "Appointment booked successfully",
  "data": {
    "id": "6738a9e1...",
    "service_id": "67389b2c...",
    "service_name": "Full House Deep Cleaning",
    "date": "2026-11-25",
    "time_slot": "10:00 AM",
    "status": "Pending",
    "price": 120.0,
    "customer_notes": "Please ring front doorbell upon arrival."
  }
}
```

---

### 4. Ratings & Feedback

#### `POST /api/ratings`
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
```json
{
  "appointment_id": "6738a9e1...",
  "service_id": "67389b2c...",
  "rating": 5.0,
  "comment": "Punctual, thorough, and left the house sparkling clean!"
}
```
- **Response `201 Created`**:
```json
{
  "success": true,
  "message": "Rating submitted successfully",
  "data": {
    "id": "6738bf54...",
    "appointment_id": "6738a9e1...",
    "rating": 5.0,
    "comment": "Punctual, thorough, and left the house sparkling clean!",
    "created_at": "2026-11-18T05:30:00Z"
  }
}
```

---

### 5. Gemini AI ServiceBot

#### `POST /api/ai/chat`
- **Request Body**:
```json
{
  "message": "I need recommendations for AC servicing and deep cleaning",
  "session_id": "optional-session-uuid"
}
```
- **Response `200 OK`**:
```json
{
  "success": true,
  "data": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "reply": "We offer master AC servicing with deep chemical wash for $45, as well as Full House Deep Cleaning for $120. Here are the direct booking options below:",
    "service_cards": [
      {
        "id": "67389b2c...",
        "name": "Air Conditioner Master Servicing",
        "category": "Appliance Repair",
        "price": 45.0,
        "rating": 4.8,
        "image_url": "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?auto=format&fit=crop&w=800&q=80"
      }
    ]
  }
}
```
