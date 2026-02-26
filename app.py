from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tracker.db"

db = SQLAlchemy()


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    unit = db.Column(db.String(120), nullable=False)
    topic = db.Column(db.String(180), nullable=False)
    priority = db.Column(db.String(20), default="Medium")
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, default="")
    completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
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
    id = db.Column(db.Integer, primary_key=True)
    exam_date = db.Column(db.Date, nullable=True)
    daily_goal = db.Column(db.Integer, default=3)
    theme = db.Column(db.String(20), default="dark")

    def to_dict(self) -> dict:
        return {
            "exam_date": self.exam_date.isoformat() if self.exam_date else None,
            "daily_goal": self.daily_goal,
            "theme": self.theme,
        }


SYLLABUS = {
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


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
        if not Setting.query.first():
            db.session.add(Setting())
            db.session.commit()

    @app.get("/")
    def index():
        return render_template("index.html", syllabus=SYLLABUS)

    @app.get("/api/bootstrap")
    def bootstrap_data():
        tasks = [task.to_dict() for task in Task.query.order_by(Task.created_at.desc()).all()]
        setting = Setting.query.first().to_dict()
        return jsonify({"tasks": tasks, "settings": setting, "syllabus": SYLLABUS})

    @app.post("/api/tasks")
    def create_task():
        data = request.get_json(force=True)
        due_date = datetime.strptime(data["due_date"], "%Y-%m-%d").date() if data.get("due_date") else None
        task = Task(
            title=data["title"].strip(),
            unit=data["unit"],
            topic=data["topic"],
            priority=data.get("priority", "Medium"),
            due_date=due_date,
            notes=data.get("notes", "").strip(),
        )
        db.session.add(task)
        db.session.commit()
        return jsonify(task.to_dict()), 201

    @app.patch("/api/tasks/<int:task_id>")
    def update_task(task_id: int):
        task = Task.query.get_or_404(task_id)
        data = request.get_json(force=True)
        if "completed" in data:
            task.completed = bool(data["completed"])
        if "priority" in data:
            task.priority = data["priority"]
        db.session.commit()
        return jsonify(task.to_dict())

    @app.delete("/api/tasks/<int:task_id>")
    def delete_task(task_id: int):
        task = Task.query.get_or_404(task_id)
        db.session.delete(task)
        db.session.commit()
        return jsonify({"ok": True})

    @app.put("/api/settings")
    def update_settings():
        setting = Setting.query.first()
        data = request.get_json(force=True)
        setting.daily_goal = int(data.get("daily_goal", setting.daily_goal))
        setting.theme = data.get("theme", setting.theme)
        exam_date_val = data.get("exam_date")
        setting.exam_date = datetime.strptime(exam_date_val, "%Y-%m-%d").date() if exam_date_val else None
        db.session.commit()
        return jsonify(setting.to_dict())

    @app.get("/api/progress")
    def progress():
        tasks = Task.query.all()
        total = len(tasks)
        completed = sum(1 for task in tasks if task.completed)
        unit_breakdown = {unit: {"total": 0, "completed": 0} for unit in SYLLABUS}
        for task in tasks:
            if task.unit not in unit_breakdown:
                unit_breakdown[task.unit] = {"total": 0, "completed": 0}
            unit_breakdown[task.unit]["total"] += 1
            if task.completed:
                unit_breakdown[task.unit]["completed"] += 1

        exam_date = Setting.query.first().exam_date
        days_left = (exam_date - date.today()).days if exam_date else None
        return jsonify(
            {
                "total": total,
                "completed": completed,
                "pending": total - completed,
                "completion_rate": round((completed / total) * 100, 1) if total else 0,
                "unit_breakdown": unit_breakdown,
                "days_left": days_left,
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
