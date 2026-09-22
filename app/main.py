import json
import os

import redis
from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy.orm import Session as DbSession

from . import models, schemas
from .database import Base, engine, get_db

app = FastAPI(title="Bodhrik API", version="0.1.0")

# Redis configuration
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "FastAPI is running!"}

@app.post("/init-db")
def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        return {"status": "ok", "message": "Database tables created successfully."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Authentication dependency
def get_current_user(x_user_id: int | None = Header(None), db: DbSession = Depends(get_db)):
    if x_user_id is None:
        raise HTTPException(status_code=401, detail="X-User-ID header missing")
    user = db.query(models.User).filter(models.User.id == x_user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.post("/sessions", response_model=schemas.SessionResponse, status_code=201)
def create_session(session: schemas.SessionCreate, db: DbSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == "parent":
        raise HTTPException(status_code=403, detail="Parents cannot create sessions")
    if current_user.role == "teacher" and session.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Teachers can only create sessions for themselves")
    
    db_session = models.Session(**session.model_dump())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@app.get("/sessions", response_model=list[schemas.SessionResponse])
def read_sessions(db: DbSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    query = db.query(models.Session)
    if current_user.role == "teacher":
        query = query.filter(models.Session.teacher_id == current_user.id)
    elif current_user.role == "parent":
        query = query.filter(models.Session.parent_id == current_user.id)
    return query.all()

@app.get("/sessions/{session_id}", response_model=schemas.SessionResponse)
def read_session(session_id: int, db: DbSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if current_user.role == "teacher" and db_session.teacher_id != current_user.id or current_user.role == "parent" and db_session.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
        
    return db_session

@app.put("/sessions/{session_id}", response_model=schemas.SessionResponse)
def update_session(session_id: int, session: schemas.SessionUpdate, db: DbSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == "parent":
        raise HTTPException(status_code=403, detail="Parents cannot update sessions")

    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if current_user.role == "teacher":
        if db_session.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to update this session")
        if session.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Cannot assign session to another teacher")
    
    for key, value in session.model_dump().items():
        setattr(db_session, key, value)
    
    db.commit()
    db.refresh(db_session)
    return db_session

@app.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: DbSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role == "parent":
        raise HTTPException(status_code=403, detail="Parents cannot delete sessions")

    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if current_user.role == "teacher" and db_session.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this session")
    
    db.delete(db_session)
    db.commit()
    return {"status": "success", "message": "Session deleted"}

@app.post("/sessions/{session_id}/evaluate", response_model=schemas.EvaluationResponse, status_code=201)
def trigger_evaluation(session_id: int, db: DbSession = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    db_session = db.query(models.Session).filter(models.Session.id == session_id).first()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Enforce RBAC
    if current_user.role == "teacher" and db_session.teacher_id != current_user.id or current_user.role == "parent" and db_session.parent_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to evaluate this session")
    
    # Create evaluation record in PostgreSQL
    db_eval = models.Evaluation(session_id=session_id, status="pending")
    db.add(db_eval)
    db.commit()
    db.refresh(db_eval)
    
    # Enqueue evaluation job to Redis
    payload = {
        "evaluation_id": db_eval.id,
        "session_id": session_id
    }
    # This will raise a redis.exceptions.ConnectionError if Redis is unavailable,
    # which authentically matches our expectation for local testing without Docker.
    redis_client.rpush("evaluation_queue", json.dumps(payload))
    
    return db_eval
