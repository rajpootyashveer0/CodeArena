from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Problem(Base):
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    input_format = Column(String, nullable=False, default="")
    output_format = Column(String, nullable=False, default="")
    constraints = Column(String, nullable=False, default="")
class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    problem_id = Column(Integer, nullable=False)
    code = Column(String, nullable=False)
    language = Column(String, nullable=False)
    status = Column(String, default="Pending")

class TestCase(Base):
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    problem_id = Column(Integer, nullable=False)
    input_data = Column(String, nullable=False)
    expected_output = Column(String, nullable=False)