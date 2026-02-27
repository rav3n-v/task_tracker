from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tracker.db"
DEFAULT_PRIORITY = "Medium"
DEFAULT_THEME = "dark"
DEFAULT_DAILY_GOAL = 3
DATE_FORMAT = "%Y-%m-%d"
ALLOWED_PRIORITIES = {"Low", "Medium", "High"}

# SQLAlchemy instance configured by create_app.
db = SQLAlchemy()
migrate = Migrate()


class User(db.Model):
    """Database model for user accounts."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tasks = db.relationship("Task", back_populates="user", cascade="all, delete-orphan")
    settings = db.relationship(
        "Setting", back_populates="user", cascade="all, delete-orphan", uselist=False
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "username": self.username}


class Task(db.Model):
    """Database model representing one study task."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    title = db.Column(db.String(160), nullable=False)
    unit = db.Column(db.String(120), nullable=False)
    topic = db.Column(db.String(180), nullable=False)
    priority = db.Column(db.String(20), default=DEFAULT_PRIORITY)
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, default="")
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", back_populates="tasks")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of this task."""

        return {
            "id": self.id,
            "title": self.title,
            "unit": self.unit,
            "topic": self.topic,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "notes": self.notes,
            "completed": self.completed,
            "created_at": self.created_at.isoformat(),
        }


class Setting(db.Model):
    """Database model for user-specific app settings."""

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True, index=True
    )
    exam_date = db.Column(db.Date, nullable=True)
    daily_goal = db.Column(db.Integer, default=DEFAULT_DAILY_GOAL)
    theme = db.Column(db.String(20), default=DEFAULT_THEME)

    user = db.relationship("User", back_populates="settings")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation of settings."""

        return {
            "exam_date": self.exam_date.isoformat() if self.exam_date else None,
            "daily_goal": self.daily_goal,
            "theme": self.theme,
        }


class StudySession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    date = db.Column(db.Date, nullable=False, index=True, default=date.today)
    duration_seconds = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RoutineTemplate(db.Model):
    __table_args__ = (
        UniqueConstraint("title", name="uq_routine_template_title"),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    display_order = db.Column(db.Integer, nullable=False, default=0)
    time_label = db.Column(db.String(120), nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "display_order": self.display_order,
            "time_label": self.time_label,
        }


class RoutineCompletion(db.Model):
    __table_args__ = (
        UniqueConstraint("user_id", "routine_id", "date", name="uq_routine_completion_user_routine_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    routine_id = db.Column(
        db.Integer, db.ForeignKey("routine_template.id"), nullable=False, index=True
    )
    date = db.Column(db.Date, nullable=False, index=True, default=date.today)
    completed = db.Column(db.Boolean, default=False, nullable=False)

    routine = db.relationship("RoutineTemplate")


class DailyRoutineTask(db.Model):
    __table_args__ = (
        UniqueConstraint("user_id", "task_name", "date", name="uq_daily_routine_user_task_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    task_name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True, default=date.today)
    completed = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_name": self.task_name,
            "date": self.date.isoformat(),
            "completed": self.completed,
        }


class SyllabusTopic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String(120), nullable=False, index=True)
    unit_name = db.Column(db.String(120), nullable=False, index=True)
    weight = db.Column(db.Float, nullable=False, default=0)
    topic_name = db.Column(db.String(255), nullable=False)


class UserSyllabusProgress(db.Model):
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_user_syllabus_topic"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    topic_id = db.Column(
        db.Integer, db.ForeignKey("syllabus_topic.id"), nullable=False, index=True
    )
    theory_completed = db.Column(db.Boolean, default=False, nullable=False)
    pyq_30_done = db.Column(db.Boolean, default=False, nullable=False)
    revision_1_done = db.Column(db.Boolean, default=False, nullable=False)
    revision_2_done = db.Column(db.Boolean, default=False, nullable=False)


class DailyTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    title = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False, index=True, default=date.today)
    completed = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "date": self.date.isoformat(),
            "completed": self.completed,
        }


class MockTest(db.Model):
    __table_args__ = (
        UniqueConstraint("user_id", "test_number", name="uq_mock_test_user_test_number"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    test_number = db.Column(db.Integer, nullable=False)
    attempted = db.Column(db.Boolean, default=False, nullable=False)
    attempt_date = db.Column(db.Date, nullable=True)
    score = db.Column(db.Float, nullable=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "test_number": self.test_number,
            "attempted": self.attempted,
            "attempt_date": self.attempt_date.isoformat() if self.attempt_date else None,
            "score": self.score,
        }


SUBJECT_WEIGHTAGE: dict[str, float] = {
    "Linear Algebra": 35,
    "Real Analysis": 35,
    "Algebra": 25,
    "Complex Analysis": 20,
    "ODE/PDE": 20,
    "Numerical Analysis": 10,
    "Unit 2 (Classical Mechanics etc.)": 10,
    "Unit 3 (Fluid Dynamics etc.)": 5,
    "Other topics combined": 20,
}


SYLLABUS: dict[str, dict[str, list[str] | str]] = {
    "Real Analysis": {
        "unit_name": "Unit 1",
        "topics": [
            "Real number system and sequences",
            "Continuity, differentiability and Riemann integration",
            "Series and uniform convergence",
            "Functions of several variables and Jacobians",
        ],
    },
    "Linear Algebra": {
        "unit_name": "Unit 1",
        "topics": [
            "Vector spaces, basis, dimension",
            "Linear transformations and matrix representations",
            "Eigenvalues, eigenvectors and diagonalization",
            "Inner product spaces and spectral theorem",
        ],
    },
    "Complex Analysis": {
        "unit_name": "Unit 1",
        "topics": [
            "Analytic functions and Cauchy-Riemann equations",
            "Cauchy integral theorem and formula",
            "Laurent series and residue calculus",
            "Conformal mappings",
        ],
    },
    "Algebra": {
        "unit_name": "Unit 1",
        "topics": [
            "Groups, subgroups and quotient groups",
            "Rings, ideals and homomorphisms",
            "Polynomial rings and irreducibility",
            "Fields and finite fields",
        ],
    },
    "ODE/PDE": {
        "unit_name": "Unit 1",
        "topics": [
            "First order equations",
            "Linear differential equations",
            "Existence and uniqueness theorems",
            "Sturm-Liouville problems",
            "First order PDEs",
            "Second order PDE classification",
            "Laplace, wave and heat equations",
            "Fourier methods and boundary value problems",
        ],
    },
    "Numerical Analysis": {
        "unit_name": "Unit 1",
        "topics": [
            "Errors and floating point arithmetic",
            "Interpolation and numerical differentiation",
            "Numerical integration",
            "Solutions of algebraic and differential equations",
        ],
    },
    "Unit 2 (Classical Mechanics etc.)": {
        "unit_name": "Unit 2",
        "topics": [
            "Lagrangian and Hamiltonian formulations",
            "Central force motion",
            "Rigid body dynamics",
        ],
    },
    "Unit 3 (Fluid Dynamics etc.)": {
        "unit_name": "Unit 3",
        "topics": [
            "Fluid statics and kinematics",
            "Euler and Navier-Stokes equations",
            "Boundary layer basics",
        ],
    },
    "Other topics combined": {
        "unit_name": "Cross-unit",
        "topics": [
            "Random variables and distributions",
            "Expectation and moments",
            "Limit theorems",
            "Estimation and hypothesis testing",
            "Euler-Lagrange equations",
            "Variational principles",
            "Constraints and Lagrange multipliers",
        ],
    },
}



def parse_optional_date(date_value: str | None) -> date | None:
    if date_value is None:
        return None
    normalized = str(date_value).strip()
    if not normalized:
        return None
    return datetime.strptime(normalized, DATE_FORMAT).date()


def require_string_field(payload: dict[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def parse_json_payload() -> tuple[dict[str, Any] | None, tuple[Response, int] | None]:
    payload = request.get_json(silent=True)
    if payload is None or not isinstance(payload, dict):
        return None, (
            jsonify({"error": "Request body must be a valid JSON object"}),
            400,
        )
    return payload, None


def validate_task_payload(
    payload: dict[str, Any], *, partial: bool = False
) -> dict[str, str]:
    errors: dict[str, str] = {}
    required_fields = ["title", "unit", "topic"]
    if not partial:
        for field in required_fields:
            if field not in payload:
                errors[field] = f"{field} is required"

    for field in required_fields:
        if field in payload and not str(payload[field]).strip():
            errors[field] = f"{field} cannot be blank"

    if "priority" in payload and str(payload["priority"]) not in ALLOWED_PRIORITIES:
        errors["priority"] = f"priority must be one of {sorted(ALLOWED_PRIORITIES)}"

    if "completed" in payload and not isinstance(payload["completed"], bool):
        errors["completed"] = "completed must be a boolean"

    if "due_date" in payload:
        due_date = payload["due_date"]
        if due_date is not None and due_date != "":
            try:
                parse_optional_date(str(due_date))
            except ValueError:
                errors["due_date"] = f"due_date must use format {DATE_FORMAT}"

    return errors


def validate_settings_payload(payload: dict[str, Any]) -> dict[str, str]:
    errors: dict[str, str] = {}

    if "daily_goal" in payload:
        value = payload["daily_goal"]
        if not isinstance(value, int) or isinstance(value, bool):
            errors["daily_goal"] = "daily_goal must be an integer"
        elif value < 0:
            errors["daily_goal"] = "daily_goal must be greater than or equal to 0"

    if "theme" in payload and not str(payload["theme"]).strip():
        errors["theme"] = "theme cannot be blank"

    if "exam_date" in payload:
        exam_date = payload["exam_date"]
        if exam_date not in (None, ""):
            try:
                parse_optional_date(str(exam_date))
            except ValueError:
                errors["exam_date"] = f"exam_date must use format {DATE_FORMAT}"

    return errors


def get_current_user() -> User | None:
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return db.session.get(User, user_id)


def require_login(
    view: Callable[..., Response | tuple[Response, int] | str],
) -> Callable[..., Response | tuple[Response, int] | str]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Response | tuple[Response, int] | str:
        if get_current_user() is None:
            return jsonify({"error": "Authentication required"}), 401
        return view(*args, **kwargs)

    return wrapped


def login_required_page(
    view: Callable[..., Response | str],
) -> Callable[..., Response | str]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Response | str:
        if get_current_user() is None:
            flash("Please login to continue.", "error")
            return redirect(url_for("render_login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required_page(
    view: Callable[..., Response | str],
) -> Callable[..., Response | str]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Response | str:
        if not session.get("is_admin"):
            flash("Admin login required.", "error")
            return redirect(url_for("render_admin"))
        return view(*args, **kwargs)

    return wrapped


def get_or_create_settings(user: User) -> Setting:
    setting = Setting.query.filter_by(user_id=user.id).first()
    if setting is None:
        setting = Setting(user_id=user.id)
        db.session.add(setting)
        db.session.commit()
    return setting


def build_task_from_payload(payload: dict[str, Any], user: User) -> Task:
    return Task(
        user_id=user.id,
        title=str(payload["title"]).strip(),
        unit=str(payload["unit"]).strip(),
        topic=str(payload["topic"]).strip(),
        priority=str(payload.get("priority", DEFAULT_PRIORITY)),
        due_date=parse_optional_date(payload.get("due_date")),
        notes=str(payload.get("notes", "")).strip(),
    )


def update_task_from_payload(task: Task, payload: dict[str, Any]) -> None:
    if "title" in payload:
        task.title = str(payload["title"]).strip()
    if "unit" in payload:
        task.unit = str(payload["unit"]).strip()
    if "topic" in payload:
        task.topic = str(payload["topic"]).strip()
    if "completed" in payload:
        task.completed = payload["completed"]
    if "priority" in payload:
        task.priority = str(payload["priority"])
    if "due_date" in payload:
        due_date = payload["due_date"]
        task.due_date = parse_optional_date(str(due_date)) if due_date else None
    if "notes" in payload:
        task.notes = str(payload["notes"]).strip()


def update_settings_from_payload(setting: Setting, payload: dict[str, Any]) -> None:
    if "daily_goal" in payload:
        setting.daily_goal = int(payload["daily_goal"])
    if "theme" in payload:
        setting.theme = str(payload["theme"]).strip()
    if "exam_date" in payload:
        setting.exam_date = parse_optional_date(payload.get("exam_date"))


def calculate_unit_breakdown(tasks: list[Task]) -> dict[str, dict[str, int]]:
    unit_breakdown: dict[str, dict[str, int]] = {
        unit: {"total": 0, "completed": 0} for unit in SYLLABUS
    }
    for task in tasks:
        unit_breakdown.setdefault(task.unit, {"total": 0, "completed": 0})
        unit_breakdown[task.unit]["total"] += 1
        if task.completed:
            unit_breakdown[task.unit]["completed"] += 1
    return unit_breakdown


def calculate_study_streak(tasks: list[Task], *, today: date | None = None) -> int:
    """Calculate consecutive study days ending today from completed tasks."""

    reference_day = today or date.today()
    completion_days = {
        task.created_at.date() for task in tasks if task.completed and task.created_at
    }

    streak = 0
    current_day = reference_day
    while current_day in completion_days:
        streak += 1
        current_day -= timedelta(days=1)
    return streak


def calculate_countdown(target_exam: date | None) -> dict[str, int]:
    """Return countdown values for exam date."""

    if target_exam is None:
        return {"days": 0, "hours": 0, "minutes": 0}

    target_datetime = datetime.combine(target_exam, datetime.min.time())
    diff_seconds = max(0, int((target_datetime - datetime.now()).total_seconds()))

    days = diff_seconds // 86400
    hours = (diff_seconds % 86400) // 3600
    minutes = (diff_seconds % 3600) // 60
    return {"days": days, "hours": hours, "minutes": minutes}


def seed_syllabus_topics() -> None:
    existing_topics = {
        (topic.subject_name, topic.topic_name)
        for topic in SyllabusTopic.query.with_entities(
            SyllabusTopic.subject_name, SyllabusTopic.topic_name
        ).all()
    }
    new_topics = []
    for subject_name, details in SYLLABUS.items():
        topics = details["topics"]
        unit_name = str(details["unit_name"])
        weight = SUBJECT_WEIGHTAGE[subject_name] / max(len(topics), 1)
        for topic_name in topics:
            if (subject_name, topic_name) not in existing_topics:
                new_topics.append(
                    SyllabusTopic(
                        subject_name=subject_name,
                        unit_name=unit_name,
                        weight=weight,
                        topic_name=topic_name,
                    )
                )
    if new_topics:
        db.session.add_all(new_topics)
        db.session.commit()


def seed_routine_templates() -> None:
    templates = [
        ("7:00 AM", "Wake up"),
        ("7:30-9:00", "Study Session 1"),
        ("9:00 AM", "Breakfast / Break"),
        ("10:00 AM", "Study Session 2"),
        ("1:00 PM", "Lunch"),
        ("2:00 PM", "Study Session 3"),
        ("6:00 PM", "Evening Revision"),
        ("8:30 PM", "Light Reading"),
    ]
    existing_titles = {
        item.title for item in RoutineTemplate.query.with_entities(RoutineTemplate.title).all()
    }
    new_items = []
    for idx, (time_label, title) in enumerate(templates):
        if title not in existing_titles:
            new_items.append(
                RoutineTemplate(title=title, display_order=idx, time_label=time_label)
            )
    if new_items:
        db.session.add_all(new_items)
        db.session.commit()


def get_or_create_daily_routine(user: User) -> list[dict[str, Any]]:
    today = date.today()
    templates = RoutineTemplate.query.order_by(RoutineTemplate.display_order.asc()).all()
    completions = RoutineCompletion.query.filter_by(user_id=user.id, date=today).all()
    completion_by_routine = {item.routine_id: item for item in completions}

    created: list[RoutineCompletion] = []
    for template in templates:
        if template.id not in completion_by_routine:
            created.append(
                RoutineCompletion(user_id=user.id, routine_id=template.id, date=today)
            )
    if created:
        db.session.add_all(created)
        db.session.commit()
        completions = RoutineCompletion.query.filter_by(user_id=user.id, date=today).all()
        completion_by_routine = {item.routine_id: item for item in completions}

    items: list[dict[str, Any]] = []
    for template in templates:
        completion = completion_by_routine.get(template.id)
        items.append(
            {
                "id": template.id,
                "title": template.title,
                "time_label": template.time_label,
                "completed": bool(completion and completion.completed),
                "date": today.isoformat(),
            }
        )
    return items


def calculate_daily_planner_streak(user: User) -> int:
    completed_days = {
        row[0]
        for row in db.session.query(DailyTask.date)
        .filter_by(user_id=user.id)
        .filter(DailyTask.completed.is_(True))
        .group_by(DailyTask.date)
        .all()
    }
    streak = 0
    current_day = date.today()
    while current_day in completed_days:
        streak += 1
        current_day -= timedelta(days=1)
    return streak


def seed_mock_tests_for_user(user: User) -> None:
    existing_numbers = {
        row[0]
        for row in db.session.query(MockTest.test_number)
        .filter_by(user_id=user.id)
        .all()
    }
    to_create = [
        MockTest(user_id=user.id, test_number=index)
        for index in range(1, 11)
        if index not in existing_numbers
    ]
    if to_create:
        db.session.add_all(to_create)
        db.session.commit()


def get_mock_test_stats(user: User) -> dict[str, Any]:
    tests = MockTest.query.filter_by(user_id=user.id).order_by(MockTest.test_number.asc()).all()
    attempted_tests = [item for item in tests if item.attempted]
    scored_tests = [item.score for item in attempted_tests if item.score is not None]
    total_tests = len(tests)
    attempted_count = len(attempted_tests)
    attempt_percent = round((attempted_count / total_tests) * 100, 1) if total_tests else 0
    average_score = round(sum(scored_tests) / len(scored_tests), 2) if scored_tests else 0
    best_score = round(max(scored_tests), 2) if scored_tests else 0
    return {
        "items": [test.to_dict() for test in tests],
        "attempted_count": attempted_count,
        "total_count": total_tests,
        "attempt_percent": attempt_percent,
        "average_score": average_score,
        "best_score": best_score,
    }


def compute_analytics_summary(user: User) -> dict[str, Any]:
    study_totals = calculate_study_time_totals(user)
    sessions = StudySession.query.filter_by(user_id=user.id).all()
    total_hours_studied = round(sum(s.duration_seconds for s in sessions) / 3600, 2)
    session_days = {s.date for s in sessions}
    average_daily_hours = round(total_hours_studied / len(session_days), 2) if session_days else 0

    routine_items = get_or_create_daily_routine(user)
    routine_completed = sum(1 for item in routine_items if item["completed"])
    routine_total = len(routine_items)
    routine_percent = round((routine_completed / routine_total) * 100, 1) if routine_total else 0

    today = date.today()
    planner_tasks = DailyTask.query.filter_by(user_id=user.id, date=today).all()
    planner_total = len(planner_tasks)
    planner_completed = sum(1 for item in planner_tasks if item.completed)
    planner_percent = round((planner_completed / planner_total) * 100, 1) if planner_total else 0

    mock_stats = get_mock_test_stats(user)
    syllabus_data = compute_syllabus_progress(user)
    syllabus_completion = round(syllabus_data["weighted_total"], 1)
    mock_attempt_percent = mock_stats["attempt_percent"]
    normalized_mock_score = round((mock_stats["average_score"] / 200) * 100, 1) if mock_stats["average_score"] else 0
    productivity_index = min(100, round(study_totals["week_hours"] / 21 * 100, 1))

    predicted_score = round(
        (0.4 * syllabus_completion)
        + (0.2 * mock_attempt_percent)
        + (0.2 * normalized_mock_score)
        + (0.2 * productivity_index),
        1,
    )
    confidence_level = "Low"
    if predicted_score >= 70:
        confidence_level = "High"
    elif predicted_score >= 45:
        confidence_level = "Medium"

    return {
        "total_hours_studied": total_hours_studied,
        "average_daily_hours": average_daily_hours,
        "daily_planner_completion_percent": planner_percent,
        "routine_consistency_percent": routine_percent,
        "mock_test_attempt_percent": mock_attempt_percent,
        "average_mock_score": mock_stats["average_score"],
        "predicted_readiness_score": predicted_score,
        "predicted_score": predicted_score,
        "confidence_level": confidence_level,
    }


def calculate_study_time_totals(user: User) -> dict[str, float]:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    sessions = StudySession.query.filter_by(user_id=user.id).all()
    today_seconds = sum(s.duration_seconds for s in sessions if s.date == today)
    week_seconds = sum(s.duration_seconds for s in sessions if s.date >= week_start)
    return {
        "today_hours": round(today_seconds / 3600, 2),
        "week_hours": round(week_seconds / 3600, 2),
    }


def compute_syllabus_progress(user: User) -> dict[str, Any]:
    topics = SyllabusTopic.query.order_by(SyllabusTopic.subject_name, SyllabusTopic.id).all()
    progress_items = UserSyllabusProgress.query.filter_by(user_id=user.id).all()
    progress_by_topic = {item.topic_id: item for item in progress_items}
    total = len(topics)

    grouped: dict[str, list[dict[str, Any]]] = {}
    counters = {"theory": 0, "pyq": 0, "rev1": 0, "rev2": 0}
    for topic in topics:
        p = progress_by_topic.get(topic.id)
        theory = bool(p and p.theory_completed)
        pyq = bool(p and p.pyq_30_done)
        rev1 = bool(p and p.revision_1_done)
        rev2 = bool(p and p.revision_2_done)
        counters["theory"] += int(theory)
        counters["pyq"] += int(pyq)
        counters["rev1"] += int(rev1)
        counters["rev2"] += int(rev2)
        grouped.setdefault(topic.subject_name, []).append(
            {
                "topic_id": topic.id,
                "topic_name": topic.topic_name,
                "theory_completed": theory,
                "pyq_30_done": pyq,
                "revision_1_done": rev1,
                "revision_2_done": rev2,
            }
        )

    percentages = {
        "theory_percent": round((counters["theory"] / total) * 100, 1) if total else 0,
        "pyq_percent": round((counters["pyq"] / total) * 100, 1) if total else 0,
        "revision_1_percent": round((counters["rev1"] / total) * 100, 1) if total else 0,
        "revision_2_percent": round((counters["rev2"] / total) * 100, 1) if total else 0,
    }

    subject_meta: dict[str, dict[str, float | str]] = {}
    for topic in topics:
        if topic.subject_name not in subject_meta:
            subject_meta[topic.subject_name] = {"unit_name": topic.unit_name, "weight": 0.0}
        subject_meta[topic.subject_name]["weight"] = float(subject_meta[topic.subject_name]["weight"]) + float(topic.weight)

    subject_breakdown = []
    for subject_name, topics_list in grouped.items():
        topic_count = len(topics_list)
        if not topic_count:
            continue
        theory_pct = (sum(1 for t in topics_list if t["theory_completed"]) / topic_count) * 100
        pyq_pct = (sum(1 for t in topics_list if t["pyq_30_done"]) / topic_count) * 100
        rev1_pct = (sum(1 for t in topics_list if t["revision_1_done"]) / topic_count) * 100
        rev2_pct = (sum(1 for t in topics_list if t["revision_2_done"]) / topic_count) * 100
        progress_score = (
            theory_pct * 0.4
            + pyq_pct * 0.3
            + rev1_pct * 0.2
            + rev2_pct * 0.1
        ) / 100
        subject_weight = float(subject_meta.get(subject_name, {}).get("weight", SUBJECT_WEIGHTAGE.get(subject_name, 0)))
        subject_contribution = progress_score * subject_weight
        subject_breakdown.append(
            {
                "subject_name": subject_name,
                "unit_name": str(subject_meta.get(subject_name, {}).get("unit_name", "Unknown Unit")),
                "weight": subject_weight,
                "theory_percent": round(theory_pct, 1),
                "pyq_percent": round(pyq_pct, 1),
                "revision_1_percent": round(rev1_pct, 1),
                "revision_2_percent": round(rev2_pct, 1),
                "progress_score": round(progress_score * 100, 1),
                "contribution": round(subject_contribution, 2),
            }
        )

    subject_breakdown.sort(key=lambda item: item["weight"], reverse=True)
    weighted_total = sum(item["contribution"] for item in subject_breakdown)
    final_score = min(200, round(20 + weighted_total, 2))

    return {
        "grouped_topics": grouped,
        "total_topics": total,
        "subject_breakdown": subject_breakdown,
        "weighted_total": round(weighted_total, 2),
        "final_score": final_score,
        **percentages,
    }


def build_dashboard_context(user: User, active_route: str) -> dict[str, Any]:
    tasks = Task.query.filter_by(user_id=user.id).all()
    setting = get_or_create_settings(user)
    total_tracked_minutes = sum(45 for task in tasks if task.completed)
    target_exam = setting.exam_date.isoformat() if setting.exam_date else None
    study_totals = calculate_study_time_totals(user)

    return {
        "syllabus": {k: v["topics"] for k, v in SYLLABUS.items()},
        "active_route": active_route,
        "study_streak": calculate_study_streak(tasks),
        "total_tracked_minutes": total_tracked_minutes,
        "target_exam": target_exam,
        "countdown": calculate_countdown(setting.exam_date),
        "today_hours": study_totals["today_hours"],
        "week_hours": study_totals["week_hours"],
    }


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "dev-secret-key"
    app.config["ADMIN_USERNAME"] = os.environ.get("ADMIN_USERNAME", "admin")
    app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD", "admin123")
    db.init_app(app)
    migrate.init_app(app, db)

    schema_checked = False

    @app.before_request
    def ensure_schema_initialized() -> None:
        nonlocal schema_checked
        if schema_checked:
            return
        db.create_all()
        seed_syllabus_topics()
        seed_routine_templates()
        schema_checked = True

    @app.get("/")
    def root_redirect() -> Response:
        if get_current_user() is not None:
            return redirect(url_for("render_dashboard"))
        return redirect(url_for("render_login"))

    @app.get("/login")
    def render_login() -> str | Response:
        if get_current_user() is not None:
            return redirect(url_for("render_dashboard"))
        return render_template("login.html")

    @app.post("/login")
    def login_page_submit() -> Response:
        username = str(request.form.get("username", "")).strip()
        password = str(request.form.get("password", ""))
        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("render_login"))

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "error")
            return redirect(url_for("render_login"))

        session["user_id"] = user.id
        flash("Welcome back!", "success")
        return redirect(url_for("render_dashboard"))

    def render_dashboard_page(active_route: str) -> str:
        user = get_current_user()
        assert user is not None

        dashboard_context = build_dashboard_context(user, active_route)

        # Always compute syllabus data once
        syllabus_data = compute_syllabus_progress(user)

        # Build progress dict exactly like old syllabus.html expected
        progress = {
            "theory": syllabus_data["theory_percent"],
            "pyq": syllabus_data["pyq_percent"],
            "revision_1": syllabus_data["revision_1_percent"],
            "revision_2": syllabus_data["revision_2_percent"],
        }

        analytics_summary = compute_analytics_summary(user)

        return render_template(
            "dashboard.html",
            **dashboard_context,

            # For syllabus partial
            grouped_topics=syllabus_data["grouped_topics"],
            progress=progress,

            # For score predictor partial
            subject_breakdown=syllabus_data["subject_breakdown"],
            predicted_score=analytics_summary["predicted_score"],
            category=analytics_summary["confidence_level"],
        )
    @app.get("/dashboard")
    @login_required_page
    def render_dashboard() -> str:
        return render_dashboard_page("dashboard")

    @app.get("/plan")
    @login_required_page
    def render_plan() -> str:
        return render_dashboard_page("plan")

    @app.get("/routine")
    @login_required_page
    def render_routine() -> str:
        return render_dashboard_page("routine")

    @app.get("/session")
    @login_required_page
    def render_session() -> str:
        return render_dashboard_page("session")

    @app.get("/tests")
    @login_required_page
    def render_tests() -> str:
        return render_dashboard_page("tests")

    @app.get("/downloads")
    @login_required_page
    def render_downloads() -> str:
        return render_dashboard_page("downloads")

    @app.get("/analytics")
    @login_required_page
    def render_analytics() -> str:
        return render_dashboard_page("analytics")

    @app.get("/resources")
    @login_required_page
    def render_resources() -> str:
        return render_dashboard_page("resources")

    @app.get("/settings")
    @login_required_page
    def render_settings() -> str:
        return render_dashboard_page("settings")

    @app.get("/syllabus")
    @login_required_page
    def render_syllabus() -> str:
        return render_dashboard_page("syllabus")

    @app.get("/score-predictor")
    @login_required_page
    def render_score_predictor() -> str:
        return render_dashboard_page("score-predictor")

    @app.get("/admin")
    def render_admin() -> str:
        return render_template("admin.html")

    @app.post("/admin")
    def admin_login_page_submit() -> Response:
        username = str(request.form.get("username", "")).strip()
        password = str(request.form.get("password", ""))

        if not username or not password:
            flash("Admin username and password are required.", "error")
            return redirect(url_for("render_admin"))

        valid_admin = (
            username == app.config["ADMIN_USERNAME"]
            and password == app.config["ADMIN_PASSWORD"]
        )
        if not valid_admin:
            flash("Invalid admin credentials.", "error")
            return redirect(url_for("render_admin"))

        session["is_admin"] = True
        flash("Admin authenticated.", "success")
        return redirect(url_for("render_admin_create_user"))

    @app.get("/admin/create-user")
    @admin_required_page
    def render_admin_create_user() -> str:
        return render_template("admin_create_user.html")

    @app.post("/admin/create-user")
    @admin_required_page
    def admin_create_user_submit() -> Response:
        username = str(request.form.get("username", "")).strip()
        password = str(request.form.get("password", ""))

        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for("render_admin_create_user"))

        if User.query.filter_by(username=username).first() is not None:
            flash("Username already exists.", "error")
            return redirect(url_for("render_admin_create_user"))

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        get_or_create_settings(user)
        flash(f"Account {username} created.", "success")
        return redirect(url_for("render_admin_create_user"))

    @app.get("/logout")
    def logout_page() -> Response:
        session.pop("user_id", None)
        session.pop("is_admin", None)
        flash("You have been logged out.", "success")
        return redirect(url_for("render_login"))

    @app.get("/api/admin/session")
    def get_admin_session() -> Response:
        return jsonify({"is_admin": bool(session.get("is_admin"))})

    @app.post("/api/admin/login")
    def admin_login() -> tuple[Response, int]:
        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None

        username = require_string_field(payload, "username")
        password = payload.get("password")
        if username is None or password is None or str(password) == "":
            return jsonify({"error": "Username and password are required"}), 400

        valid_admin = (
            username == app.config["ADMIN_USERNAME"]
            and str(password) == app.config["ADMIN_PASSWORD"]
        )
        if not valid_admin:
            return jsonify({"error": "Invalid admin credentials"}), 401

        session["is_admin"] = True
        return jsonify({"is_admin": True}), 200

    @app.post("/api/admin/logout")
    def admin_logout() -> Response:
        session.pop("is_admin", None)
        return jsonify({"ok": True})

    @app.get("/api/me")
    def get_me() -> Response:
        user = get_current_user()
        return jsonify({"user": user.to_dict() if user else None})

    @app.post("/api/register")
    def register() -> tuple[Response, int]:
        if not session.get("is_admin"):
            return jsonify({"error": "Admin authentication required"}), 403

        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None
        username = require_string_field(payload, "username")
        password = payload.get("password")

        if username is None or password is None or str(password) == "":
            return jsonify({"error": "Username and password are required"}), 400

        if User.query.filter_by(username=username).first() is not None:
            return jsonify({"error": "Username already exists"}), 409

        user = User(username=username)
        user.set_password(str(password))
        db.session.add(user)
        db.session.commit()
        get_or_create_settings(user)
        return jsonify({"user": user.to_dict()}), 201

    @app.post("/api/login")
    def login() -> tuple[Response, int]:
        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None
        username = require_string_field(payload, "username")
        password = payload.get("password")

        if username is None or password is None or str(password) == "":
            return jsonify({"error": "Username and password are required"}), 400

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(str(password)):
            return jsonify({"error": "Invalid username or password"}), 401

        session["user_id"] = user.id
        return jsonify({"user": user.to_dict()}), 200

    @app.post("/api/logout")
    def logout() -> Response:
        session.pop("user_id", None)
        return jsonify({"ok": True})

    @app.get("/api/bootstrap")
    @require_login
    def get_bootstrap_data() -> Response:
        user = get_current_user()
        assert user is not None
        task_models = (
            Task.query.filter_by(user_id=user.id).order_by(Task.created_at.desc()).all()
        )
        tasks = [task.to_dict() for task in task_models]
        setting_model = get_or_create_settings(user)
        total_tracked_minutes = sum(45 for task in task_models if task.completed)
        return jsonify(
            {
                "tasks": tasks,
                "settings": setting_model.to_dict(),
                "syllabus": {k: v["topics"] for k, v in SYLLABUS.items()},
                "user": user.to_dict(),
                "study_streak": calculate_study_streak(task_models),
                "total_tracked_minutes": total_tracked_minutes,
                "study_time": calculate_study_time_totals(user),
                "target_exam": setting_model.exam_date.isoformat() if setting_model.exam_date else None,
                "countdown": calculate_countdown(setting_model.exam_date),
            }
        )


    @app.post("/api/study-session")
    @require_login
    def create_study_session() -> tuple[Response, int]:
        user = get_current_user()
        assert user is not None
        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None

        duration = payload.get("duration_seconds")
        if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
            return jsonify({"error": "duration_seconds must be a positive integer"}), 400

        session_model = StudySession(user_id=user.id, duration_seconds=duration, date=date.today())
        db.session.add(session_model)
        db.session.commit()

        totals = calculate_study_time_totals(user)
        return jsonify({"ok": True, **totals}), 201

    @app.get("/api/daily-routine")
    @require_login
    def get_daily_routine() -> Response:
        user = get_current_user()
        assert user is not None
        items = get_or_create_daily_routine(user)
        completed_count = sum(1 for item in items if item["completed"])
        total_count = len(items)
        completion_percentage = round((completed_count / total_count) * 100, 1) if total_count else 0
        return jsonify(
            {
                "items": items,
                "tasks": items,
                "completed_count": completed_count,
                "total_count": total_count,
                "completion_percentage": completion_percentage,
                "completed_percent": completion_percentage,
            }
        )

    @app.post("/api/daily-routine")
    @require_login
    def update_daily_routine() -> Response:
        user = get_current_user()
        assert user is not None
        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None

        routine_id = payload.get("routine_id")
        if not isinstance(routine_id, int) or isinstance(routine_id, bool):
            return jsonify({"error": "routine_id must be an integer"}), 400

        completion = RoutineCompletion.query.filter_by(
            user_id=user.id,
            routine_id=routine_id,
            date=date.today(),
        ).first()
        if completion is None:
            completion = RoutineCompletion(user_id=user.id, routine_id=routine_id, date=date.today(), completed=False)
            db.session.add(completion)

        completion.completed = not completion.completed
        db.session.commit()

        items = get_or_create_daily_routine(user)
        completed_count = sum(1 for item in items if item["completed"])
        total_count = len(items)
        completion_percentage = round((completed_count / total_count) * 100, 1) if total_count else 0
        return jsonify(
            {
                "ok": True,
                "items": items,
                "tasks": items,
                "completed_count": completed_count,
                "total_count": total_count,
                "completion_percentage": completion_percentage,
                "completed_percent": completion_percentage,
            }
        )

    @app.get("/api/daily-planner")
    @require_login
    def get_daily_planner() -> Response:
        user = get_current_user()
        assert user is not None
        raw_date = request.args.get("date")
        try:
            planner_date = parse_optional_date(raw_date) if raw_date else date.today()
        except ValueError:
            return jsonify({"error": f"date must use format {DATE_FORMAT}"}), 400
        tasks = DailyTask.query.filter_by(user_id=user.id, date=planner_date).order_by(DailyTask.created_at.asc()).all()
        total_count = len(tasks)
        completed_count = sum(1 for task in tasks if task.completed)
        completion_percentage = round((completed_count / total_count) * 100, 1) if total_count else 0
        return jsonify(
            {
                "date": planner_date.isoformat(),
                "items": [task.to_dict() for task in tasks],
                "completed_count": completed_count,
                "total_count": total_count,
                "completion_percentage": completion_percentage,
                "streak": calculate_daily_planner_streak(user),
            }
        )

    @app.post("/api/daily-planner")
    @require_login
    def create_daily_planner_task() -> tuple[Response, int]:
        user = get_current_user()
        assert user is not None
        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None

        title = require_string_field(payload, "title")
        if title is None:
            return jsonify({"error": "title is required"}), 400

        try:
            task_date = parse_optional_date(payload.get("date")) if payload.get("date") else date.today()
        except ValueError:
            return jsonify({"error": f"date must use format {DATE_FORMAT}"}), 400
        task = DailyTask(user_id=user.id, title=title, date=task_date)
        db.session.add(task)
        db.session.commit()
        return jsonify(task.to_dict()), 201

    @app.patch("/api/daily-planner/<int:task_id>")
    @require_login
    def toggle_daily_planner_task(task_id: int) -> Response:
        user = get_current_user()
        assert user is not None
        task = DailyTask.query.filter_by(id=task_id, user_id=user.id).first()
        if task is None:
            return jsonify({"error": "Task not found"}), 404
        task.completed = not task.completed
        db.session.commit()
        return jsonify(task.to_dict())

    @app.delete("/api/daily-planner/<int:task_id>")
    @require_login
    def delete_daily_planner_task(task_id: int) -> Response:
        user = get_current_user()
        assert user is not None
        task = DailyTask.query.filter_by(id=task_id, user_id=user.id).first()
        if task is None:
            return jsonify({"error": "Task not found"}), 404
        db.session.delete(task)
        db.session.commit()
        return jsonify({"ok": True})

    @app.patch("/api/mock-tests/<int:test_number>")
    @require_login
    def update_mock_test(test_number: int) -> Response:
        user = get_current_user()
        assert user is not None
        if test_number < 1 or test_number > 10:
            return jsonify({"error": "test_number must be between 1 and 10"}), 400

        seed_mock_tests_for_user(user)
        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None

        test = MockTest.query.filter_by(user_id=user.id, test_number=test_number).first()
        assert test is not None

        if "attempted" in payload:
            if not isinstance(payload["attempted"], bool):
                return jsonify({"error": "attempted must be a boolean"}), 400
            test.attempted = payload["attempted"]

        if "attempt_date" in payload:
            if payload["attempt_date"] in (None, ""):
                test.attempt_date = None
            else:
                try:
                    test.attempt_date = parse_optional_date(str(payload["attempt_date"]))
                except ValueError:
                    return jsonify({"error": f"attempt_date must use format {DATE_FORMAT}"}), 400

        if "score" in payload:
            if payload["score"] in (None, ""):
                test.score = None
            elif isinstance(payload["score"], (int, float)) and not isinstance(payload["score"], bool):
                test.score = float(payload["score"])
            else:
                return jsonify({"error": "score must be a number or null"}), 400

        db.session.commit()
        return jsonify({"item": test.to_dict(), **get_mock_test_stats(user)})

    @app.get("/api/mock-tests")
    @require_login
    def get_mock_tests() -> Response:
        user = get_current_user()
        assert user is not None
        seed_mock_tests_for_user(user)
        return jsonify(get_mock_test_stats(user))

    @app.get("/api/analytics-summary")
    @require_login
    def get_analytics_summary() -> Response:
        user = get_current_user()
        assert user is not None
        return jsonify(compute_analytics_summary(user))

    @app.get("/api/syllabus-progress")
    @require_login
    def get_syllabus_progress() -> Response:
        user = get_current_user()
        assert user is not None
        return jsonify(compute_syllabus_progress(user))

    @app.post("/api/syllabus-progress")
    @require_login
    def update_syllabus_progress() -> Response:
        user = get_current_user()
        assert user is not None
        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None

        topic_id = payload.get("topic_id")
        field = payload.get("field")
        value = payload.get("value")
        valid_fields = {"theory_completed", "pyq_30_done", "revision_1_done", "revision_2_done"}

        if not isinstance(topic_id, int) or isinstance(topic_id, bool):
            return jsonify({"error": "topic_id must be an integer"}), 400
        if field not in valid_fields:
            return jsonify({"error": "field is invalid"}), 400
        if not isinstance(value, bool):
            return jsonify({"error": "value must be a boolean"}), 400

        topic = db.session.get(SyllabusTopic, topic_id)
        if topic is None:
            return jsonify({"error": "Topic not found"}), 404

        progress = UserSyllabusProgress.query.filter_by(user_id=user.id, topic_id=topic_id).first()
        if progress is None:
            progress = UserSyllabusProgress(user_id=user.id, topic_id=topic_id)
            db.session.add(progress)

        setattr(progress, field, value)
        db.session.commit()
        return jsonify({"ok": True})

    @app.get("/api/tasks")
    @require_login
    def list_tasks() -> Response:
        user = get_current_user()
        assert user is not None
        tasks = (
            Task.query.filter_by(user_id=user.id).order_by(Task.created_at.desc()).all()
        )
        return jsonify({"tasks": [task.to_dict() for task in tasks]}), 200

    @app.post("/api/tasks")
    @require_login
    def create_task() -> tuple[Response, int]:
        user = get_current_user()
        assert user is not None
        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None
        errors = validate_task_payload(payload)
        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400
        task = build_task_from_payload(payload, user)
        db.session.add(task)
        db.session.commit()
        return jsonify(task.to_dict()), 201

    @app.patch("/api/tasks/<int:task_id>")
    @require_login
    def update_task(task_id: int) -> Response:
        user = get_current_user()
        assert user is not None
        task = Task.query.filter_by(id=task_id, user_id=user.id).first()
        if task is None:
            return jsonify({"error": "Task not found"}), 404
        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None
        errors = validate_task_payload(payload, partial=True)
        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400
        update_task_from_payload(task, payload)
        db.session.commit()
        return jsonify(task.to_dict())

    @app.delete("/api/tasks/<int:task_id>")
    @require_login
    def delete_task(task_id: int) -> Response:
        user = get_current_user()
        assert user is not None
        task = Task.query.filter_by(id=task_id, user_id=user.id).first()
        if task is None:
            return jsonify({"error": "Task not found"}), 404
        db.session.delete(task)
        db.session.commit()
        return jsonify({"ok": True}), 200

    @app.put("/api/settings")
    @require_login
    def update_settings() -> Response:
        user = get_current_user()
        assert user is not None
        setting = get_or_create_settings(user)
        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None
        errors = validate_settings_payload(payload)
        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400
        update_settings_from_payload(setting, payload)
        db.session.commit()
        return jsonify(setting.to_dict())

    @app.get("/api/progress")
    @require_login
    def get_progress() -> Response:
        user = get_current_user()
        assert user is not None
        tasks = Task.query.filter_by(user_id=user.id).all()
        total = len(tasks)
        completed = sum(task.completed for task in tasks)
        exam_date = get_or_create_settings(user).exam_date
        days_left = (exam_date - date.today()).days if exam_date else None

        return jsonify(
            {
                "total": total,
                "completed": completed,
                "pending": total - completed,
                "completion_rate": round((completed / total) * 100, 1) if total else 0,
                "unit_breakdown": calculate_unit_breakdown(tasks),
                "days_left": days_left,
                "study_streak": calculate_study_streak(tasks),
                "total_tracked_minutes": sum(45 for task in tasks if task.completed),
                "study_time": calculate_study_time_totals(user),
                "target_exam": exam_date.isoformat() if exam_date else None,
                "countdown": calculate_countdown(exam_date),
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
