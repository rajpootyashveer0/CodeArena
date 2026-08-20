from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from database import engine, Base, get_db
from models import User, Problem, Submission, TestCase
from judge import run_python_code

from schemas import (
    UserCreate,
    UserResponse,
    UserLogin,
    Token,
    ProblemCreate,
    ProblemResponse,
    SubmissionCreate,
    SubmissionResponse,
    TestCaseCreate,
    TestCaseResponse
)

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_admin
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="CodeArena API")


@app.get("/")
def home():
    return {"message": "Welcome to CodeArena!"}


@app.post("/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    hashed_password = hash_password(user.password)

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@app.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):

    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        user.password,
        existing_user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        data={"sub": str(existing_user.id)}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.post("/token")
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        data={"sub": str(user.id)}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.post("/problems", response_model=ProblemResponse)
def create_problem(
    problem: ProblemCreate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    new_problem = Problem(
        title=problem.title,
        description=problem.description,
        difficulty=problem.difficulty,
        input_format=problem.input_format,
        output_format=problem.output_format,
        constraints=problem.constraints
    )

    db.add(new_problem)
    db.commit()
    db.refresh(new_problem)

    return new_problem


@app.get("/problems", response_model=list[ProblemResponse])
def get_problems(
    difficulty: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Problem)

    if difficulty:
        query = query.filter(
            Problem.difficulty == difficulty
        )

    return query.all()


@app.get("/problems/{problem_id}", response_model=ProblemResponse)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    problem = db.query(Problem).filter(
        Problem.id == problem_id
    ).first()

    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found"
        )

    return problem



@app.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/submissions", response_model=SubmissionResponse)
def create_submission(
    submission: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    problem = db.query(Problem).filter(
        Problem.id == submission.problem_id
    ).first()

    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found"
        )

    new_submission = Submission(
        user_id=current_user.id,
        problem_id=submission.problem_id,
        code=submission.code,
        language=submission.language,
        status="Pending"
    )

    db.add(new_submission)
    db.commit()
    db.refresh(new_submission)

    if submission.language.lower() == "python":
        test_cases = db.query(TestCase).filter(
            TestCase.problem_id == submission.problem_id
        ).all()

        if not test_cases:
            new_submission.status = "No Test Cases"
        else:
            all_passed = True

            for test_case in test_cases:
                result = run_python_code(
                    submission.code,
                    test_case.input_data
                )

                if not result["success"]:
                    new_submission.status = "Runtime Error"
                    all_passed = False
                    break

                if result["output"] != test_case.expected_output:
                    new_submission.status = "Wrong Answer"
                    all_passed = False
                    break

            if all_passed:
                new_submission.status = "Accepted"

    else:
        new_submission.status = "Language Not Supported"

    db.commit()
    db.refresh(new_submission)

    return new_submission

@app.get("/submissions", response_model=list[SubmissionResponse])
def get_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Submission).filter(
        Submission.user_id == current_user.id
    ).all()

@app.post("/test-cases", response_model=TestCaseResponse)
def create_test_case(
    test_case: TestCaseCreate,
    db: Session = Depends(get_db)
):
    problem = db.query(Problem).filter(
        Problem.id == test_case.problem_id
    ).first()

    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found"
        )

    new_test_case = TestCase(
        problem_id=test_case.problem_id,
        input_data=test_case.input_data,
        expected_output=test_case.expected_output
    )

    db.add(new_test_case)
    db.commit()
    db.refresh(new_test_case)

    return new_test_case

@app.get("/test-cases/{problem_id}", response_model=list[TestCaseResponse])
def get_test_cases(
    problem_id: int,
    db: Session = Depends(get_db)
):
    problem = db.query(Problem).filter(
        Problem.id == problem_id
    ).first()

    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found"
        )

    return db.query(TestCase).filter(
        TestCase.problem_id == problem_id
    ).all()

@app.put("/problems/{problem_id}", response_model=ProblemResponse)
def update_problem(
    problem_id: int,
    problem_data: ProblemCreate,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    problem = db.query(Problem).filter(
        Problem.id == problem_id
    ).first()

    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found"
        )

    problem.title = problem_data.title
    problem.description = problem_data.description
    problem.difficulty = problem_data.difficulty
    problem.input_format = problem_data.input_format
    problem.output_format = problem_data.output_format
    problem.constraints = problem_data.constraints

    db.commit()
    db.refresh(problem)

    return problem

@app.delete("/problems/{problem_id}")
def delete_problem(
    problem_id: int,
    db: Session = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    problem = db.query(Problem).filter(
        Problem.id == problem_id
    ).first()

    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found"
        )

    db.delete(problem)
    db.commit()

    return {
        "message": "Problem deleted successfully"
    }

@app.get("/submissions/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.user_id == current_user.id
    ).first()

    if not submission:
        raise HTTPException(
            status_code=404,
            detail="Submission not found"
        )

    return submission

@app.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    submissions = db.query(Submission).filter(
        Submission.user_id == current_user.id
    ).all()

    total_submissions = len(submissions)

    accepted = sum(
        1 for submission in submissions
        if submission.status == "Accepted"
    )

    wrong_answers = sum(
        1 for submission in submissions
        if submission.status == "Wrong Answer"
    )

    runtime_errors = sum(
        1 for submission in submissions
        if submission.status == "Runtime Error"
    )

    solved_problems = len({
        submission.problem_id
        for submission in submissions
        if submission.status == "Accepted"
    })

    return {
        "total_submissions": total_submissions,
        "accepted": accepted,
        "wrong_answers": wrong_answers,
        "runtime_errors": runtime_errors,
        "problems_solved": solved_problems
    }