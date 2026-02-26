from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from flask import Flask, Response, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tracker.db"
DEFAULT_PRIORITY = "Medium"
DEFAULT_THEME = "dark"
DEFAULT_DAILY_GOAL = 3
DATE_FORMAT = "%Y-%m-%d"

# SQLAlchemy instance configured by create_app.
db = SQLAlchemy()


class Task(db.Model):
    """Database model representing one study task."""

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    unit = db.Column(db.String(120), nullable=False)
    topic = db.Column(db.String(180), nullable=False)
    priority = db.Column(db.String(20), default=DEFAULT_PRIORITY)
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, default="")
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    """Database model for singleton app settings."""

    id = db.Column(db.Integer, primary_key=True)
    exam_date = db.Column(db.Date, nullable=True)
    daily_goal = db.Column(db.Integer, default=DEFAULT_DAILY_GOAL)
    theme = db.Column(db.String(20), default=DEFAULT_THEME)

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


def get_or_create_settings() -> Setting:
    """Fetch the singleton settings row, creating it when absent."""

    setting = Setting.query.first()
    if setting is None:
        setting = Setting()
        db.session.add(setting)
        db.session.commit()
    return setting


def build_task_from_payload(payload: dict[str, Any]) -> Task:
    """Create a Task model from API payload values."""

    return Task(
        title=str(payload["title"]).strip(),
        unit=str(payload["unit"]),
        topic=str(payload["topic"]),
        priority=str(payload.get("priority", DEFAULT_PRIORITY)),
        due_date=parse_optional_date(payload.get("due_date")),
        notes=str(payload.get("notes", "")).strip(),
    )


def update_task_from_payload(task: Task, payload: dict[str, Any]) -> None:
    """Apply mutable task fields from API payload."""

    if "completed" in payload:
        task.completed = bool(payload["completed"])
    if "priority" in payload:
        task.priority = str(payload["priority"])


def update_settings_from_payload(setting: Setting, payload: dict[str, Any]) -> None:
    """Apply mutable settings fields from API payload."""

    setting.daily_goal = int(payload.get("daily_goal", setting.daily_goal))
    setting.theme = str(payload.get("theme", setting.theme))
    setting.exam_date = parse_optional_date(payload.get("exam_date"))


def calculate_unit_breakdown(tasks: list[Task]) -> dict[str, dict[str, int]]:
    """Aggregate task totals and completions per unit."""

    unit_breakdown: dict[str, dict[str, int]] = {unit: {"total": 0, "completed": 0} for unit in SYLLABUS}
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
    db.init_app(app)

    with app.app_context():
        db.create_all()
        get_or_create_settings()

    @app.get("/")
    def render_index() -> str:
        """Render the main application shell."""

        return render_template("index.html", syllabus=SYLLABUS)

    @app.get("/api/bootstrap")
    def get_bootstrap_data() -> Response:
        """Return tasks, settings, and syllabus for initial client load."""

        task_models = Task.query.order_by(Task.created_at.desc()).all()
        tasks = [task.to_dict() for task in task_models]
        setting = get_or_create_settings().to_dict()
        return jsonify({"tasks": tasks, "settings": setting, "syllabus": SYLLABUS})

    @app.post("/api/tasks")
    def create_task() -> tuple[Response, int]:
        """Create a task from JSON payload and persist it."""

        payload: dict[str, Any] = request.get_json(force=True)
        task = build_task_from_payload(payload)
        db.session.add(task)
        db.session.commit()
        return jsonify(task.to_dict()), 201

    @app.patch("/api/tasks/<int:task_id>")
    def update_task(task_id: int) -> Response:
        """Update mutable task fields for a specific task."""

        task = Task.query.get_or_404(task_id)
        payload: dict[str, Any] = request.get_json(force=True)
        update_task_from_payload(task, payload)
        db.session.commit()
        return jsonify(task.to_dict())

    @app.delete("/api/tasks/<int:task_id>")
    def delete_task(task_id: int) -> Response:
        """Delete a task by id."""

        task = Task.query.get_or_404(task_id)
        db.session.delete(task)
        db.session.commit()
        return jsonify({"ok": True})

    @app.put("/api/settings")
    def update_settings() -> Response:
        """Update user settings and return persisted state."""

        setting = get_or_create_settings()
        payload: dict[str, Any] = request.get_json(force=True)
        update_settings_from_payload(setting, payload)
        db.session.commit()
        return jsonify(setting.to_dict())

    @app.get("/api/progress")
    def get_progress() -> Response:
        """Return aggregate progress metrics and exam countdown."""

        tasks = Task.query.all()
        total = len(tasks)
        completed = sum(task.completed for task in tasks)
        exam_date = get_or_create_settings().exam_date
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
