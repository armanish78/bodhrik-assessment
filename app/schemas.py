from pydantic import BaseModel


class SessionBase(BaseModel):
    title: str
    teacher_id: int
    parent_id: int
    child_name: str

class SessionCreate(SessionBase):
    pass

class SessionUpdate(SessionBase):
    pass

class SessionResponse(SessionBase):
    id: int

    class Config:
        from_attributes = True

class EvaluationResponse(BaseModel):
    id: int
    session_id: int
    status: str
    result_data: str | None = None

    class Config:
        from_attributes = True
