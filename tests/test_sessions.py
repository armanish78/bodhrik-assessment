from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Note: These tests expect a running PostgreSQL database.
# Because PostgreSQL is not available locally, most of these will fail with Connection Refused.
# We are NOT faking or mocking the database.

# 1. Authentication
def test_missing_auth_header():
    response = client.get("/sessions")
    assert response.status_code == 401
    assert response.json()["detail"] == "X-User-ID header missing"


# 2. Admin RBAC
def test_admin_access():
    response = client.get("/sessions/1", headers={"X-User-ID": "1"})
    assert response.status_code == 200


# 3. Teacher RBAC — own session
def test_teacher_access_own():
    response = client.get("/sessions/1", headers={"X-User-ID": "2"})
    assert response.status_code == 200


# 4. Teacher RBAC — other teacher
def test_teacher_access_other():
    response = client.get("/sessions/1", headers={"X-User-ID": "3"})
    assert response.status_code == 403


# 5. Parent RBAC — own session
def test_parent_access_own():
    response = client.get("/sessions/1", headers={"X-User-ID": "4"})
    assert response.status_code == 200


# 6. Parent RBAC — other parent
def test_parent_access_other():
    response = client.get("/sessions/1", headers={"X-User-ID": "5"})
    assert response.status_code == 403


# 7. CRUD — Create + Read
def test_crud_create_read():
    # Admin creates a session
    create_response = client.post(
        "/sessions",
        headers={"X-User-ID": "1"},
        json={
            "title": "Science Tutoring",
            "teacher_id": 2,
            "parent_id": 4,
            "child_name": "Charlie"
        }
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    # Teacher reads it
    read_response = client.get(f"/sessions/{session_id}", headers={"X-User-ID": "2"})
    assert read_response.status_code == 200
    assert read_response.json()["title"] == "Science Tutoring"


# 8. CRUD — Update + Delete
def test_crud_update_delete():
    # Admin creates a temporary session
    create_response = client.post(
        "/sessions",
        headers={"X-User-ID": "1"},
        json={
            "title": "Temp Session",
            "teacher_id": 2,
            "parent_id": 4,
            "child_name": "Temp"
        }
    )
    assert create_response.status_code == 201
    session_id = create_response.json()["id"]

    # Teacher updates it
    update_response = client.put(
        f"/sessions/{session_id}",
        headers={"X-User-ID": "2"},
        json={
            "title": "Updated Temp Session",
            "teacher_id": 2,
            "parent_id": 4,
            "child_name": "Temp"
        }
    )
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Updated Temp Session"

    # Teacher deletes it
    delete_response = client.delete(f"/sessions/{session_id}", headers={"X-User-ID": "2"})
    assert delete_response.status_code == 200

    # Verify deletion
    read_response = client.get(f"/sessions/{session_id}", headers={"X-User-ID": "2"})
    assert read_response.status_code == 404


# 9. Evaluation
def test_evaluation_trigger():
    # Teacher triggers evaluation on their own session
    response = client.post("/sessions/1/evaluate", headers={"X-User-ID": "2"})
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


# 10. Evaluation RBAC
def test_evaluation_rbac_unauthorized():
    # Another teacher tries to trigger evaluation on teacher 2's session
    response = client.post("/sessions/1/evaluate", headers={"X-User-ID": "3"})
    assert response.status_code == 403
