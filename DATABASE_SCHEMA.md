# Database Design & Schema Documentation (MongoDB Atlas)

## Database Technology: MongoDB Atlas
- **Engine**: MongoDB Atlas 6.0+ (Replica Set / Sharded Cloud)
- **Async Driver**: `motor` (AsyncIO non-blocking driver for Python)
- **Database Name**: `servicebookingdb`

---

## 📊 Entity-Relationship (ER) Architecture

```
┌─────────────────────────────────┐               ┌─────────────────────────────────┐
│              USERS              │               │            SERVICES             │
├─────────────────────────────────┤               ├─────────────────────────────────┤
│ _id: ObjectId                   │◄──────┐       │ _id: ObjectId                   │
│ name: String                    │       │       │ provider_id: String (FK)        │────┐
│ email: String (Unique)          │       │       │ provider_name: String           │    │
│ password: String (PBKDF2 hash)  │       │       │ name: String                    │    │
│ role: "customer" | "provider"   │       │       │ description: String             │    │
│ phone: String                   │       │       │ category: String                │    │
│ institution_name: String?       │       │       │ price: Double                   │    │
│ avatar_url: String              │       │       │ duration_minutes: Integer       │    │
│ is_active: Boolean              │       │       │ image_url: String               │    │
│ created_at / updated_at: ISO    │       │       │ is_featured: Boolean            │    │
└────────────────┬────────────────┘       │       │ rating: Double                  │    │
                 │ 1                      │       │ total_reviews: Integer          │    │
                 │                        │       │ available_days: Array[String]   │    │
                 │                        │       │ time_slots: Array[String]       │    │
                 ▼ N                      │       │ is_active: Boolean              │    │
┌─────────────────────────────────┐       │       └────────────────┬────────────────┘    │
│          APPOINTMENTS           │       │                        │ 1                   │
├─────────────────────────────────┤       │                        │                     │
│ _id: ObjectId                   │       │                        │                     │
│ user_id: String (FK)            │───────┘                        │                     │
│ user_name / user_email: String  │                                │                     │
│ service_id: String (FK)         │◄───────────────────────────────┘                     │
│ service_name / category: String │                                                      │
│ service_price: Double           │                                                      │
│ service_image: String           │◄─────────────────────────────────────────────────────┘
│ date: String (YYYY-MM-DD)       │  (Synced when provider updates service)
│ time_slot: String ("10:00 AM")  │
│ status: "Pending" | "Confirmed" │
│         "Completed"|"Cancelled" │
│ customer_notes: String          │
│ created_at / updated_at: ISO    │
└────────────────┬────────────────┘
                 │ 1
                 │
                 ▼ 1
┌─────────────────────────────────┐               ┌─────────────────────────────────┐
│             RATINGS             │               │          NOTIFICATIONS          │
├─────────────────────────────────┤               ├─────────────────────────────────┤
│ _id: ObjectId                   │               │ _id: ObjectId                   │
│ appointment_id: String (Unique) │               │ user_id: String (FK)            │
│ service_id: String (FK)         │               │ title: String                   │
│ user_id: String (FK)            │               │ message: String                 │
│ user_name: String               │               │ type: String                    │
│ rating: Double (1.0 to 5.0)     │               │ reference_id: String?           │
│ comment: String                 │               │ is_read: Boolean                │
│ created_at / updated_at: ISO    │               │ created_at: ISO String          │
└─────────────────────────────────┘               └─────────────────────────────────┘

┌─────────────────────────────────┐
│           AI_SESSIONS           │
├─────────────────────────────────┤
│ _id: ObjectId                   │
│ user_id: String (FK)            │
│ title: String                   │
│ messages: Array[Embedded]       │
│   - id: String                  │
│   - text: String                │
│   - is_user: Boolean            │
│   - timestamp: ISO String       │
│   - service_cards: Array?       │
│ created_at / updated_at: ISO    │
└─────────────────────────────────┘
```

---

## 🗄️ Collections Specification

### 1. `users`
Stores credentials, roles, and profile metadata for both Customers and Service Providers.
| Field | Type | Description | Index |
|---|---|---|---|
| `_id` | `ObjectId` | Primary Key | `{_id: 1}` |
| `name` | `String` | Full name of the individual or contact person | |
| `email` | `String` | Lowercased email address | `{email: 1}`, `unique=True` |
| `password` | `String` | Salted PBKDF2-HMAC-SHA256 password hash | |
| `role` | `String` | `"customer"` or `"provider"` | |
| `phone` | `String?` | Optional phone number | |
| `institution_name`| `String?` | Organization / Business name for providers | |
| `avatar_url` | `String` | Profile image URL | |
| `is_active` | `Boolean` | Account status flag (default: `True`) | |
| `created_at` | `String` | ISO8601 UTC creation timestamp | |
| `updated_at` | `String` | ISO8601 UTC last modification timestamp | |

### 2. `services`
The master catalog of discoverable services offered by providers.
| Field | Type | Description | Index |
|---|---|---|---|
| `_id` | `ObjectId` | Primary Key | `{_id: 1}` |
| `provider_id` | `String` | References `users._id` of the offering provider | `{provider_id: 1}` |
| `provider_name` | `String` | Business name snapshot | |
| `name` | `String` | Title of the service | `{name: "text"}` |
| `description` | `String` | Detailed description of the service | |
| `category` | `String` | Service classification (e.g. `Home Cleaning`) | `{category: 1}` |
| `price` | `Double` | Base service price in USD | |
| `duration_minutes`| `Integer`| Duration of service in minutes | |
| `image_url` | `String` | Cover image URL | |
| `is_featured` | `Boolean` | HOT / Featured banner carousel promotion flag | `{is_featured: 1}` |
| `rating` | `Double` | Aggregate average rating score (e.g. `4.85`) | |
| `total_reviews` | `Integer` | Count of customer reviews | |
| `available_days` | `Array[String]`| Operating days (e.g. `["Monday", "Tuesday"]`) | |
| `time_slots` | `Array[String]`| Standard schedule slots (e.g. `["10:00 AM"]`) | |
| `is_active` | `Boolean` | Visibility flag | |

### 3. `appointments`
Manages customer bookings, provider assignments, and status transitions.
| Field | Type | Description | Index |
|---|---|---|---|
| `_id` | `ObjectId` | Primary Key | `{_id: 1}` |
| `user_id` | `String` | References booking `users._id` | `{user_id: 1, status: 1}` |
| `user_name` | `String` | Customer name snapshot | |
| `user_email` | `String` | Customer email snapshot | |
| `service_id` | `String` | References `services._id` | `{service_id: 1, date: 1, time_slot: 1}` (Compound) |
| `service_name` | `String` | Service name snapshot (synced on update) | |
| `service_category`| `String` | Service category snapshot | |
| `service_price` | `Double` | Service price snapshot | |
| `service_image` | `String` | Service image URL snapshot (synced on update) | |
| `date` | `String` | Booking date (`YYYY-MM-DD`) | |
| `time_slot` | `String` | Scheduled time slot (e.g. `"10:00 AM"`) | |
| `status` | `String` | `"Pending"` \| `"Confirmed"` \| `"Completed"` \| `"Cancelled"` | |
| `customer_notes` | `String?` | Optional customer instructions | |
| `created_at` / `updated_at` | `String` | ISO8601 UTC timestamps | |

### 4. `ratings`
Client feedback and rating scores for completed appointments.
| Field | Type | Description | Index |
|---|---|---|---|
| `_id` | `ObjectId` | Primary Key | `{_id: 1}` |
| `appointment_id` | `String` | References `appointments._id` | `{appointment_id: 1}`, `unique=True` |
| `service_id` | `String` | References `services._id` | `{service_id: 1}` |
| `user_id` | `String` | References `users._id` | `{user_id: 1}` |
| `user_name` | `String` | Reviewer name | |
| `rating` | `Double` | Star score (1.0 to 5.0) | |
| `comment` | `String` | Customer written feedback | |
| `created_at` / `updated_at` | `String` | ISO8601 UTC timestamps | |

### 5. `notifications`
Push-style inbox alerts for appointment status changes and updates.
| Field | Type | Description | Index |
|---|---|---|---|
| `_id` | `ObjectId` | Primary Key | `{_id: 1}` |
| `user_id` | `String` | Target recipient `users._id` | `{user_id: 1, is_read: 1}` |
| `title` | `String` | Notification headline | |
| `message` | `String` | Body text | |
| `type` | `String` | `"booking"` \| `"review"` \| `"system"` | |
| `reference_id` | `String?` | Linked appointment or service ID | |
| `is_read` | `Boolean` | Read tracking flag | |
| `created_at` | `String` | ISO8601 UTC timestamp | |

### 6. `ai_sessions`
Persistent multi-turn conversational sessions with Gemini AI assistant.
| Field | Type | Description | Index |
|---|---|---|---|
| `_id` | `ObjectId` | Primary Key | `{_id: 1}` |
| `user_id` | `String` | Associated `users._id` | `{user_id: 1, updated_at: -1}` |
| `title` | `String` | Generated session preview title | |
| `messages` | `Array[Object]` | Embedded conversation message history | |
| `created_at` / `updated_at` | `String` | ISO8601 UTC timestamps | |

---

## ⚡ Setup & Database Initialization Instructions

### Step 1: MongoDB Atlas Provisioning
1. Sign in to [MongoDB Atlas](https://cloud.mongodb.com/).
2. Create a Shared M0 (Free) or Serverless database cluster.
3. In **Database Access**, create a user with `readWriteAnyDatabase` privileges.
4. In **Network Access**, add IP whitelist `0.0.0.0/0` (allowing Vercel serverless and mobile clients).
5. Copy the connection string into `service_booking_management_app_backend/.env`:
   ```env
   MONGODB_URL=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
   DATABASE_NAME=servicebookingdb
   ```

### Step 2: Automated Index Creation
Compound indexes and unique constraints are automatically registered at FastAPI startup via:
```python
# app/core/database.py
await db.users.create_index("email", unique=True)
await db.appointments.create_index([("service_id", 1), ("date", 1), ("time_slot", 1)])
await db.appointments.create_index([("user_id", 1), ("status", 1)])
await db.services.create_index("category")
await db.services.create_index("is_featured")
await db.ratings.create_index("appointment_id", unique=True)
await db.notifications.create_index([("user_id", 1), ("is_read", 1)])
```

### Step 3: Run Database Seeder
To populate catalog items and demo test users:
```bash
cd service_booking_management_app_backend
python scripts/seed_data.py
```
