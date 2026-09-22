from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Note: These tests expect a running PostgreSQL database.
# Because PostgreSQL is not available locally, most of these will fail with Connection Refused.
# We are NOT faking or mocking the database.

def test_missing_auth_header():
    # This should pass even without DB because header check is before DB query
    response = client.get("/sessions")
    assert response.status_code == 401
    assert response.json()["detail"] == "X-User-ID header missing"

def test_invalid_user_id():
    response = client.get("/sessions", headers={"X-User-ID": "999"})
    # Fails with 500 if no DB, otherwise 401
    assert response.status_code == 401

def test_admin_access():
    # Admin (role="admin", id=1) should be able to read any session
    response = client.get("/sessions/1", headers={"X-User-ID": "1"})
    assert response.status_code == 200

def test_teacher_access_own():
    # Teacher accessing their own session
    response = client.get("/sessions/1", headers={"X-User-ID": "2"})
    assert response.status_code == 200

def test_teacher_access_other():
    # Teacher accessing another teacher's session
    response = client.get("/sessions/1", headers={"X-User-ID": "3"})
    assert response.status_code == 403

def test_parent_access_own():
    # Parent accessing their own child's session
    response = client.get("/sessions/1", headers={"X-User-ID": "4"})
    assert response.status_code == 200

def test_parent_access_other():
    # Parent accessing another parent's session
    response = client.get("/sessions/1", headers={"X-User-ID": "5"})
    assert response.status_code == 403

def test_parent_cannot_create():
    response = client.post("/sessions", headers={"X-User-ID": "4"}, json={
        "title": "Math Tutoring",
        "teacher_id": 2,
        "parent_id": 4,
        "child_name": "Alice"
    })
    assert response.status_code == 403

def test_teacher_cannot_create_for_other():
    response = client.post("/sessions", headers={"X-User-ID": "2"}, json={
        "title": "Math Tutoring",
        "teacher_id": 3,
        "parent_id": 4,
        "child_name": "Alice"
    })
    assert response.status_code == 403

def test_authorized_update_succeeds():
    response = client.put("/sessions/1", headers={"X-User-ID": "2"}, json={
        "title": "Math Tutoring Updated",
        "teacher_id": 2,
        "parent_id": 4,
        "child_name": "Alice"
    })
    assert response.status_code == 200

def test_unauthorized_update_rejected():
    response = client.put("/sessions/1", headers={"X-User-ID": "3"}, json={
        "title": "Math Tutoring Updated",
        "teacher_id": 2,
        "parent_id": 4,
        "child_name": "Alice"
    })
    assert response.status_code == 403

def test_authorized_delete_succeeds():
    from app.database import SessionLocal
    from app.models import Session
    db = SessionLocal()
    existing = db.query(Session).filter(Session.id == 200).first()
    if existing:
        db.delete(existing)
        db.commit()
        
    new_session = Session(id=200, title="To Delete", teacher_id=2, parent_id=4, child_name="Del")
    db.add(new_session)
    db.commit()
    db.close()

    response = client.delete("/sessions/200", headers={"X-User-ID": "2"})
    assert response.status_code == 200

def test_unauthorized_delete_rejected():
    response = client.delete("/sessions/1", headers={"X-User-ID": "3"})
    assert response.status_code == 403

def test_read_sessions_filtering():
    response = client.get("/sessions", headers={"X-User-ID": "1"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_verify_cascade_delete():
    from app.database import SessionLocal
    from app.models import Evaluation, Session
    db = SessionLocal()
    
    # Cleanup beforehand to ensure idempotency
    for sid in [100, 101, 102]:
        existing = db.query(Session).filter(Session.id == sid).first()
        if existing:
            db.delete(existing)
    db.commit()
    
    # Create a session without evaluation
    s_no_eval = Session(id=100, title="No Eval", teacher_id=2, parent_id=4, child_name="Bob")
    db.add(s_no_eval)
    # Create a session with evaluation
    s_with_eval = Session(id=101, title="With Eval", teacher_id=2, parent_id=4, child_name="Charlie")
    db.add(s_with_eval)
    db.commit()
    
    s_with_eval_id = s_with_eval.id
    s_no_eval_id = s_no_eval.id
    
    # Create an unrelated session and evaluation to verify they are not deleted
    s_unrelated = Session(id=102, title="Unrelated", teacher_id=2, parent_id=4, child_name="Dave")
    db.add(s_unrelated)
    db.commit()
    unrelated_id = s_unrelated.id
    eval_unrelated = Evaluation(session_id=unrelated_id, status="pending")
    db.add(eval_unrelated)
    
    eval_record = Evaluation(session_id=s_with_eval_id, status="pending")
    db.add(eval_record)
    db.commit()
    
    eval_id = eval_record.id
    unrelated_eval_id = eval_unrelated.id
    
    # Delete session without evaluation
    response = client.delete(f"/sessions/{s_no_eval_id}", headers={"X-User-ID": "2"})
    assert response.status_code == 200
    
    # Delete session with evaluation
    response = client.delete(f"/sessions/{s_with_eval_id}", headers={"X-User-ID": "2"})
    assert response.status_code == 200
    
    # Verify evaluation is deleted
    assert db.query(Evaluation).filter(Evaluation.id == eval_id).first() is None
    
    # Verify unrelated session and evaluation still exist
    unrelated_session_db = db.query(Session).filter(Session.id == unrelated_id).first()
    assert unrelated_session_db is not None
    assert db.query(Evaluation).filter(Evaluation.id == unrelated_eval_id).first() is not None
    
    # Cleanup unrelated to remain idempotent
    db.delete(unrelated_session_db)
    db.commit()
    db.close()

# --- Phase 4 Evaluation Tests ---

def test_evaluate_unauthenticated():
    response = client.post("/sessions/1/evaluate")
    assert response.status_code == 401

def test_evaluate_nonexistent_session():
    response = client.post("/sessions/999/evaluate", headers={"X-User-ID": "1"})
    assert response.status_code == 404

def test_admin_can_evaluate_any():
    response = client.post("/sessions/1/evaluate", headers={"X-User-ID": "1"})
    assert response.status_code == 201
    assert response.json()["status"] == "pending"

def test_teacher_can_evaluate_own():
    response = client.post("/sessions/1/evaluate", headers={"X-User-ID": "2"})
    assert response.status_code == 201
    assert response.json()["status"] == "pending"

def test_teacher_cannot_evaluate_other():
    response = client.post("/sessions/1/evaluate", headers={"X-User-ID": "3"})
    assert response.status_code == 403

def test_parent_can_evaluate_own():
    response = client.post("/sessions/1/evaluate", headers={"X-User-ID": "4"})
    assert response.status_code == 201
    assert response.json()["status"] == "pending"

def test_parent_cannot_evaluate_other():
    response = client.post("/sessions/1/evaluate", headers={"X-User-ID": "5"})
    assert response.status_code == 403
