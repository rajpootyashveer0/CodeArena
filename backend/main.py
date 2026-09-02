from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware

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
    TestCaseResponse,
    LeaderboardResponse
)

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    get_current_admin
)


# =========================
# DATABASE
# =========================

Base.metadata.create_all(bind=engine)


# =========================
# APP
# =========================

app = FastAPI(title="CodeArena API")


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# HOME
# =========================

@app.get("/")
def home():
    return {
        "message": "Welcome to CodeArena!"
    }


# =========================
# SIGNUP
# =========================

@app.post("/signup", response_model=UserResponse)
def signup(
    user: UserCreate,
    db: Session = Depends(get_db)
):

    existing_user = db.query(User).filter(
        User.email == user.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )

    existing_username = db.query(User).filter(
        User.username == user.username
    ).first()

    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Username already taken"
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


# =========================
# LOGIN
# =========================

@app.post("/login", response_model=Token)
def login(
    user: UserLogin,
    db: Session = Depends(get_db)
):

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
        data={
            "sub": str(existing_user.id)
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# =========================
# OAUTH TOKEN
# =========================

@app.post("/token")
def token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.email == form_data.username
    ).first()

    if not user or not verify_password(
        form_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        data={
            "sub": str(user.id)
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# =========================
# CURRENT USER
# =========================

@app.get("/me", response_model=UserResponse)
def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user


# =========================================================
# PROBLEMS
# =========================================================


# =========================
# CREATE PROBLEM
# =========================

@app.post(
    "/problems",
    response_model=ProblemResponse
)
def create_problem(
    problem: ProblemCreate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin)
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


# =========================
# GET ALL PROBLEMS
# =========================

@app.get(
    "/problems",
    response_model=list[ProblemResponse]
)
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


# =========================
# GET SINGLE PROBLEM
# =========================

@app.get(
    "/problems/{problem_id}",
    response_model=ProblemResponse
)
def get_problem(
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

    return problem


# =========================
# UPDATE PROBLEM
# =========================

@app.put(
    "/problems/{problem_id}",
    response_model=ProblemResponse
)
def update_problem(
    problem_id: int,
    problem_data: ProblemCreate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin)
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


# =========================
# DELETE PROBLEM
# =========================

@app.delete("/problems/{problem_id}")
def delete_problem(
    problem_id: int,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin)
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


# =========================================================
# TEST CASES
# =========================================================


# =========================
# CREATE TEST CASE
# =========================

@app.post(
    "/test-cases",
    response_model=TestCaseResponse
)
def create_test_case(
    test_case: TestCaseCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
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


# =========================
# GET TEST CASES
# =========================

@app.get(
    "/test-cases/{problem_id}",
    response_model=list[TestCaseResponse]
)
def get_test_cases(
    problem_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
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

# =========================
# UPDATE TEST CASE
# =========================

@app.put(
    "/test-cases/{test_case_id}",
    response_model=TestCaseResponse
)
def update_test_case(
    test_case_id: int,
    test_case_data: TestCaseCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):

    test_case = db.query(TestCase).filter(
        TestCase.id == test_case_id
    ).first()

    if not test_case:
        raise HTTPException(
            status_code=404,
            detail="Test case not found"
        )

    problem = db.query(Problem).filter(
        Problem.id == test_case_data.problem_id
    ).first()

    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found"
        )

    test_case.problem_id = test_case_data.problem_id
    test_case.input_data = test_case_data.input_data
    test_case.expected_output = (
        test_case_data.expected_output
    )

    db.commit()
    db.refresh(test_case)

    return test_case

# =========================
# DELETE TEST CASE
# =========================

@app.delete("/test-cases/{test_case_id}")
def delete_test_case(
    test_case_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):

    test_case = db.query(TestCase).filter(
        TestCase.id == test_case_id
    ).first()

    if not test_case:
        raise HTTPException(
            status_code=404,
            detail="Test case not found"
        )

    db.delete(test_case)
    db.commit()

    return {
        "message": "Test case deleted successfully"
    }

# =========================================================
# RUN CODE
# =========================================================

@app.post("/run")
def run_code(
    submission: SubmissionCreate,
    db: Session = Depends(get_db)
):

    problem = db.query(Problem).filter(
        Problem.id == submission.problem_id
    ).first()

    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found"
        )

    if submission.language.lower() != "python":
        return {
            "success": False,
            "output": "Language Not Supported"
        }

    test_case = db.query(TestCase).filter(
        TestCase.problem_id == submission.problem_id
    ).first()

    if not test_case:
        return {
            "success": False,
            "output": "No test cases available"
        }

    result = run_python_code(
        submission.code,
        test_case.input_data
    )

    return {
        "success": result["success"],
        "output": result["output"]
    }


# =========================================================
# SUBMISSIONS
# =========================================================


# =========================
# CREATE SUBMISSION
# =========================

@app.post(
    "/submissions",
    response_model=SubmissionResponse
)
def create_submission(
    submission: SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # -------------------------
    # Check problem
    # -------------------------

    problem = db.query(Problem).filter(
        Problem.id == submission.problem_id
    ).first()

    if not problem:
        raise HTTPException(
            status_code=404,
            detail="Problem not found"
        )

    # -------------------------
    # Create submission
    # -------------------------

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

    # -------------------------
    # Language check
    # -------------------------

    if submission.language.lower() != "python":

        new_submission.status = "Language Not Supported"

    else:

        # -------------------------
        # Get ALL test cases
        # -------------------------

        test_cases = db.query(TestCase).filter(
            TestCase.problem_id == submission.problem_id
        ).all()

        # -------------------------
        # No test cases
        # -------------------------

        if not test_cases:

            new_submission.status = "No Test Cases"

        else:

            all_passed = True

            # -------------------------
            # Run every test case
            # -------------------------

            for test_case in test_cases:

                result = run_python_code(
                    submission.code,
                    test_case.input_data
                )

                # Runtime error
                if not result["success"]:

                    new_submission.status = "Runtime Error"
                    all_passed = False

                    break

                # Wrong answer
                actual_output = str(
                    result["output"]
                ).strip()

                expected_output = str(
                    test_case.expected_output
                ).strip()

                if actual_output != expected_output:

                    new_submission.status = "Wrong Answer"
                    all_passed = False

                    break

            # -------------------------
            # All tests passed
            # -------------------------

            if all_passed:

                new_submission.status = "Accepted"

    # -------------------------
    # Save final verdict
    # -------------------------

    db.commit()
    db.refresh(new_submission)

    return new_submission


# =========================
# GET MY SUBMISSIONS
# =========================

@app.get(
    "/submissions",
    response_model=list[SubmissionResponse]
)
def get_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    return db.query(Submission).filter(
        Submission.user_id == current_user.id
    ).order_by(
        Submission.id.desc()
    ).all()


# =========================
# GET SINGLE SUBMISSION
# =========================

@app.get(
    "/submissions/{submission_id}",
    response_model=SubmissionResponse
)
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


# =========================================================
# STATS
# =========================================================

@app.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    submissions = db.query(Submission).filter(
        Submission.user_id == current_user.id
    ).all()

    # -------------------------
    # Basic statistics
    # -------------------------

    total_submissions = len(submissions)

    accepted = sum(
        1
        for submission in submissions
        if submission.status == "Accepted"
    )

    wrong_answers = sum(
        1
        for submission in submissions
        if submission.status == "Wrong Answer"
    )

    runtime_errors = sum(
        1
        for submission in submissions
        if submission.status == "Runtime Error"
    )

    # -------------------------
    # Unique solved problems
    # -------------------------

    solved_problem_ids = {
        submission.problem_id
        for submission in submissions
        if submission.status == "Accepted"
    }

    problems_solved = len(
        solved_problem_ids
    )

    # -------------------------
    # Difficulty statistics
    # -------------------------

    easy_solved = 0
    medium_solved = 0
    hard_solved = 0

    for problem_id in solved_problem_ids:

        problem = db.query(Problem).filter(
            Problem.id == problem_id
        ).first()

        if not problem:
            continue

        if problem.difficulty == "Easy":
            easy_solved += 1

        elif problem.difficulty == "Medium":
            medium_solved += 1

        elif problem.difficulty == "Hard":
            hard_solved += 1

    return {
        "total_submissions": total_submissions,
        "accepted": accepted,
        "wrong_answers": wrong_answers,
        "runtime_errors": runtime_errors,
        "problems_solved": problems_solved,
        "easy_solved": easy_solved,
        "medium_solved": medium_solved,
        "hard_solved": hard_solved
    }


# =========================================================
# DASHBOARD
# =========================================================

@app.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    submissions = db.query(Submission).filter(
        Submission.user_id == current_user.id
    ).all()

    # -------------------------
    # Submission statistics
    # -------------------------

    total_submissions = len(submissions)

    accepted = sum(
        1
        for submission in submissions
        if submission.status == "Accepted"
    )

    wrong_answers = sum(
        1
        for submission in submissions
        if submission.status == "Wrong Answer"
    )

    runtime_errors = sum(
        1
        for submission in submissions
        if submission.status == "Runtime Error"
    )

    # -------------------------
    # Unique solved problems
    # -------------------------

    solved_problem_ids = {
        submission.problem_id
        for submission in submissions
        if submission.status == "Accepted"
    }

    problems_solved = len(
        solved_problem_ids
    )

    # -------------------------
    # Difficulty-wise solved
    # -------------------------

    easy_solved = 0
    medium_solved = 0
    hard_solved = 0

    for problem_id in solved_problem_ids:

        problem = db.query(Problem).filter(
            Problem.id == problem_id
        ).first()

        if not problem:
            continue

        if problem.difficulty == "Easy":
            easy_solved += 1

        elif problem.difficulty == "Medium":
            medium_solved += 1

        elif problem.difficulty == "Hard":
            hard_solved += 1

    # -------------------------
    # Dashboard response
    # -------------------------

    return {
        "user": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email
        },

        "stats": {
            "total_submissions": total_submissions,
            "accepted": accepted,
            "wrong_answers": wrong_answers,
            "runtime_errors": runtime_errors,
            "problems_solved": problems_solved,
            "easy_solved": easy_solved,
            "medium_solved": medium_solved,
            "hard_solved": hard_solved
        }
    }

# =========================================================
# LEADERBOARD
# =========================================================

@app.get(
    "/leaderboard",
    response_model=list[LeaderboardResponse]
)
def get_leaderboard(
    db: Session = Depends(get_db)
):

    users = db.query(User).all()

    leaderboard = []

    # --------------------------------
    # Calculate stats for every user
    # --------------------------------

    for user in users:

        submissions = db.query(Submission).filter(
            Submission.user_id == user.id
        ).all()

        # -----------------------------
        # Total submissions
        # -----------------------------

        total_submissions = len(submissions)

        # -----------------------------
        # Accepted submissions
        # -----------------------------

        accepted_submissions = sum(
            1
            for submission in submissions
            if submission.status == "Accepted"
        )

        # -----------------------------
        # Unique solved problems
        # -----------------------------

        solved_problem_ids = {
            submission.problem_id
            for submission in submissions
            if submission.status == "Accepted"
        }

        problems_solved = len(
            solved_problem_ids
        )

        # -----------------------------
        # Acceptance rate
        # -----------------------------

        if total_submissions > 0:
            acceptance_rate = round(
                (
                    accepted_submissions
                    / total_submissions
                ) * 100,
                2
            )
        else:
            acceptance_rate = 0.0

        # -----------------------------
        # Add user
        # -----------------------------

        leaderboard.append({
            "user_id": user.id,
            "username": user.username,
            "problems_solved": problems_solved,
            "accepted_submissions": accepted_submissions,
            "total_submissions": total_submissions,
            "acceptance_rate": acceptance_rate
        })

    # --------------------------------
    # Sort leaderboard
    # --------------------------------

    leaderboard.sort(
        key=lambda user: (
            -user["problems_solved"],
            -user["accepted_submissions"],
            -user["acceptance_rate"],
            user["total_submissions"]
        )
    )

    # --------------------------------
    # Assign ranks
    # --------------------------------

    for index, user in enumerate(
        leaderboard,
        start=1
    ):
        user["rank"] = index

    return leaderboard