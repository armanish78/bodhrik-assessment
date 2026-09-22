from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    role = Column(String, nullable=False) # 'admin', 'teacher', 'parent'

    # Relationships
    sessions_taught = relationship("Session", foreign_keys="[Session.teacher_id]", back_populates="teacher")
    sessions_as_parent = relationship("Session", foreign_keys="[Session.parent_id]", back_populates="parent")

class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # The child this session is for
    child_name = Column(String, nullable=False)

    # Relationships
    teacher = relationship("User", foreign_keys=[teacher_id], back_populates="sessions_taught")
    parent = relationship("User", foreign_keys=[parent_id], back_populates="sessions_as_parent")
    evaluations = relationship("Evaluation", back_populates="session", cascade="all, delete-orphan")

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    status = Column(String, default="pending")
    result_data = Column(Text, nullable=True)

    # Relationships
    session = relationship("Session", back_populates="evaluations")
