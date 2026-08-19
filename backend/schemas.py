from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str

class ProblemBase(BaseModel):
    title: str
    description: str
    difficulty: str


class ProblemCreate(ProblemBase):
    pass


class ProblemResponse(ProblemBase):
    id: int

    class Config:
        from_attributes = True


class SubmissionCreate(BaseModel):
    problem_id: int
    code: str
    language: str


class SubmissionResponse(BaseModel):
    id: int
    user_id: int
    problem_id: int
    code: str
    language: str
    status: str

    class Config:
        from_attributes = True

class SubmissionCreate(BaseModel):
    problem_id: int
    code: str
    language: str


class SubmissionResponse(BaseModel):
    id: int
    user_id: int
    problem_id: int
    code: str
    language: str
    status: str

    class Config:
        from_attributes = True