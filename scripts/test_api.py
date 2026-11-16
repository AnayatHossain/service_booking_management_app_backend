import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from starlette.testclient import TestClient
from app.main import app

def test_endpoints():
    with TestClient(app) as client:
        # 1. Health check
        res = client.get("/api/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("PASS: /api/health returned 200")

        # 2. List services
        res = client.get("/api/services")
        assert res.status_code == 200, f"Services fetch failed: {res.text}"
        services = res.json()["data"]
        assert len(services) > 0, "No services returned"
        print(f"PASS: /api/services returned {len(services)} services")

        # 3. Categories
        res = client.get("/api/services/categories")
        assert res.status_code == 200
        print(f"PASS: /api/services/categories returned: {res.json()['data']}")

        # 4. Auth login
        res = client.post("/api/auth/login", json={
            "email": "testuser@example.com",
            "password": "password123"
        })
        assert res.status_code == 200, f"Login failed: {res.text}"
        token = res.json()["data"]["access_token"]
        user_name = res.json()["data"]["user"]["name"]
        print(f"PASS: /api/auth/login succeeded for {user_name}")

        # 5. Auth Me
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        print(f"PASS: /api/auth/me authenticated as {res.json()['data']['email']}")

        # 6. Check slot availability
        target_service = services[0]
        res = client.get(f"/api/appointments/availability?service_id={target_service['id']}&date=2026-11-20")
        assert res.status_code == 200
        slots = res.json()["data"]["slots"]
        print(f"PASS: /api/appointments/availability returned {len(slots)} slots")

        # 7. Create Appointment
        res = client.post(
            "/api/appointments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "service_id": target_service["id"],
                "date": "2026-11-20",
                "time_slot": slots[0]["slot"],
                "customer_notes": "Please ring the front doorbell on arrival."
            }
        )
        assert res.status_code == 201, f"Appointment booking failed: {res.text}"
        apt_id = res.json()["data"]["id"]
        print(f"PASS: /api/appointments booked appointment {apt_id} successfully")

        # 8. Prevent duplicate booking (Slot conflict test)
        res_conflict = client.post(
            "/api/appointments",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "service_id": target_service["id"],
                "date": "2026-11-20",
                "time_slot": slots[0]["slot"]
            }
        )
        assert res_conflict.status_code == 409, f"Conflict check failed, expected 409: {res_conflict.text}"
        print("PASS: Conflict check prevented double booking (returned 409 Conflict as required)")

        # 9. My Appointments
        res = client.get("/api/appointments/my", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        my_apts = res.json()["data"]
        print(f"PASS: /api/appointments/my returned {len(my_apts)} user appointments")

        # 10. AI Assistant Chat
        ai_res = client.post("/api/ai/chat", json={
            "message": "Which home cleaning service do you recommend?"
        })
        assert ai_res.status_code == 200
        reply = ai_res.json()["data"]["reply"]
        print(f"PASS: /api/ai/chat responded: {reply[:80]}...")

        # 11. Cancel Appointment
        res_cancel = client.patch(f"/api/appointments/{apt_id}/cancel", headers={"Authorization": f"Bearer {token}"})
        assert res_cancel.status_code == 200
        assert res_cancel.json()["data"]["status"] == "Cancelled"
        print(f"PASS: /api/appointments/{apt_id}/cancel successfully cancelled booking")

        print("\nALL 11 BACKEND API SUITE TESTS PASSED PERFECTLY!")

if __name__ == "__main__":
    test_endpoints()
