from __future__ import annotations

from datetime import date, datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from flask import Flask, Response, jsonify, render_template, request, session
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
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


SYLLABUS: dict[str, list[str]] = {
    "Mathematical Analysis": [
        "Real number system and sequences",
        "Continuity, differentiability and Riemann integration",
        "Series and uniform convergence",
        "Functions of several variables and Jacobians",
    ],
    "Linear Algebra": [
        "Vector spaces, basis, dimension",
        "Linear transformations and matrix representations",
        "Eigenvalues, eigenvectors and diagonalization",
        "Inner product spaces and spectral theorem",
    ],
    "Complex Analysis": [
        "Analytic functions and Cauchy-Riemann equations",
        "Cauchy integral theorem and formula",
        "Laurent series and residue calculus",
        "Conformal mappings",
    ],
    "Algebra": [
        "Groups, subgroups and quotient groups",
        "Rings, ideals and homomorphisms",
        "Polynomial rings and irreducibility",
        "Fields and finite fields",
    ],
    "Ordinary Differential Equations": [
        "First order equations",
        "Linear differential equations",
        "Existence and uniqueness theorems",
        "Sturm-Liouville problems",
    ],
    "Partial Differential Equations": [
        "First order PDEs",
        "Second order PDE classification",
        "Laplace, wave and heat equations",
        "Fourier methods and boundary value problems",
    ],
    "Numerical Analysis": [
        "Errors and floating point arithmetic",
        "Interpolation and numerical differentiation",
        "Numerical integration",
        "Solutions of algebraic and differential equations",
    ],
    "Calculus of Variations": [
        "Euler-Lagrange equations",
        "Variational principles",
        "Constraints and Lagrange multipliers",
    ],
    "Classical Mechanics": [
        "Lagrangian and Hamiltonian formulations",
        "Central force motion",
        "Rigid body dynamics",
    ],
    "Probability and Statistics": [
        "Random variables and distributions",
        "Expectation and moments",
        "Limit theorems",
        "Estimation and hypothesis testing",
    ],
}


def parse_optional_date(date_value: str | None) -> date | None:
    """Parse an ISO date string (YYYY-MM-DD) when present."""

    return datetime.strptime(date_value, DATE_FORMAT).date() if date_value else None


def parse_json_payload() -> tuple[dict[str, Any] | None, tuple[Response, int] | None]:
    """Parse JSON request body and return either payload or a JSON error response."""

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
    """Validate task creation/update payload and return field-level error messages."""

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


def get_or_create_settings(user: User) -> Setting:
    """Fetch the user's settings row, creating it when absent."""

    setting = Setting.query.filter_by(user_id=user.id).first()
    if setting is None:
        setting = Setting(user_id=user.id)
        db.session.add(setting)
        db.session.commit()
    return setting


def build_task_from_payload(payload: dict[str, Any], user: User) -> Task:
    """Create a Task model from API payload values."""

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
    """Apply mutable task fields from API payload."""

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
    """Apply mutable settings fields from API payload."""

    setting.daily_goal = int(payload.get("daily_goal", setting.daily_goal))
    setting.theme = str(payload.get("theme", setting.theme))
    setting.exam_date = parse_optional_date(payload.get("exam_date"))


def calculate_unit_breakdown(tasks: list[Task]) -> dict[str, dict[str, int]]:
    """Aggregate task totals and completions per unit."""

    unit_breakdown: dict[str, dict[str, int]] = {
        unit: {"total": 0, "completed": 0} for unit in SYLLABUS
    }
    for task in tasks:
        unit_breakdown.setdefault(task.unit, {"total": 0, "completed": 0})
        unit_breakdown[task.unit]["total"] += 1
        if task.completed:
            unit_breakdown[task.unit]["completed"] += 1
    return unit_breakdown


def create_app() -> Flask:
    """Application factory that wires config, models, and routes."""

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "dev-secret-key"
    db.init_app(app)
    migrate.init_app(app, db)

    @app.get("/")
    def render_index() -> str:
        """Render the main application shell."""

        return render_template("index.html", syllabus=SYLLABUS)

    @app.get("/api/me")
    def get_me() -> Response:
        user = get_current_user()
        return jsonify({"user": user.to_dict() if user else None})

    @app.post("/api/register")
    def register() -> tuple[Response, int]:
        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None
        username = str(payload["username"]).strip()
        password = str(payload["password"])

        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400

        if User.query.filter_by(username=username).first() is not None:
            return jsonify({"error": "Username already exists"}), 409

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        get_or_create_settings(user)
        session["user_id"] = user.id
        return jsonify({"user": user.to_dict()}), 201

    @app.post("/api/login")
    def login() -> tuple[Response, int]:
        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None
        username = str(payload["username"]).strip()
        password = str(payload["password"])

        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
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
        """Return tasks, settings, and syllabus for initial client load."""

        user = get_current_user()
        assert user is not None
        task_models = (
            Task.query.filter_by(user_id=user.id).order_by(Task.created_at.desc()).all()
        )
        tasks = [task.to_dict() for task in task_models]
        setting = get_or_create_settings(user).to_dict()
        return jsonify(
            {
                "tasks": tasks,
                "settings": setting,
                "syllabus": SYLLABUS,
                "user": user.to_dict(),
            }
        )

    @app.get("/api/tasks")
    @require_login
    def list_tasks() -> Response:
        """List all tasks for the logged-in user in reverse creation order."""

        user = get_current_user()
        assert user is not None
        tasks = (
            Task.query.filter_by(user_id=user.id).order_by(Task.created_at.desc()).all()
        )
        return jsonify({"tasks": [task.to_dict() for task in tasks]}), 200

    @app.post("/api/tasks")
    @require_login
    def create_task() -> tuple[Response, int]:
        """Create a task from JSON payload and persist it."""

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
        """Update mutable task fields for a specific task."""

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
        """Delete a task by id."""

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
        """Update user settings and return persisted state."""

        user = get_current_user()
        assert user is not None
        setting = get_or_create_settings(user)
        payload, error = parse_json_payload()
        if error:
            return error
        assert payload is not None
        update_settings_from_payload(setting, payload)
        db.session.commit()
        return jsonify(setting.to_dict())

    @app.get("/api/progress")
    @require_login
    def get_progress() -> Response:
        """Return aggregate progress metrics and exam countdown."""

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
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
