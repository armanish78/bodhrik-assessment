from app import models
from app.database import Base, SessionLocal, engine

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Create users if they don't exist
try:
    admin = models.User(id=1, username="admin", role="admin")
    teacher1 = models.User(id=2, username="teacher1", role="teacher")
    teacher2 = models.User(id=3, username="teacher2", role="teacher")
    parent1 = models.User(id=4, username="parent1", role="parent")
    parent2 = models.User(id=5, username="parent2", role="parent")
    db.add_all([admin, teacher1, teacher2, parent1, parent2])
    db.commit()
except Exception:
    db.rollback()

# Create session 1 if it doesn't exist
try:
    session = models.Session(id=1, title="Math", teacher_id=2, parent_id=4, child_name="Alice")
    db.add(session)
    db.commit()
except Exception:
    db.rollback()

db.close()
print("Database seeded successfully.")
