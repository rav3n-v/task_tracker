from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import Mock

import app as tracker_app
from app import Task, User, create_app, db, get_or_create_settings


def _create_user(username="user", password="pass123"):
    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def _create_task(
    user_id, *, title="Read chapter", unit="Algebra", topic="Groups", **overrides
):
    task = Task(user_id=user_id, title=title, unit=unit, topic=topic, **overrides)
    db.session.add(task)
    db.session.commit()
    return task


def _admin_login(client, username="admin", password="admin123"):
    return client.post(
        "/api/admin/login", json={"username": username, "password": password}
    )


def test_first_request_auto_creates_schema_for_account_creation(tmp_path):
    database_path = tmp_path / "fresh_runtime.db"
    flask_app = create_app()
    flask_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
        SECRET_KEY="test-secret",
    )
    client = flask_app.test_client()

    admin_response = client.post(
        "/api/admin/login", json={"username": "admin", "password": "admin123"}
    )
    assert admin_response.status_code == 200

    register_response = client.post(
        "/api/register", json={"username": "runtime_user", "password": "secret"}
    )
    assert register_response.status_code == 201

    with flask_app.app_context():
        created_user = User.query.filter_by(username="runtime_user").first()
        assert created_user is not None


def test_root_redirects_to_login_when_unauthenticated(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_register_hashes_password(client, app):
    _admin_login(client)
    response = client.post(
        "/api/register", json={"username": "alice", "password": "secret"}
    )

    assert response.status_code == 201
    with app.app_context():
        user = User.query.filter_by(username="alice").first()
        assert user is not None
        assert user.password_hash != "secret"
        assert user.check_password("secret") is True

    me = client.get("/api/me")
    assert me.get_json()["user"] is None


def test_dashboard_requires_login_redirect(client):
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_sidebar_page_routes_require_login(client):
    for path in [
        "/plan",
        "/routine",
        "/session",
        "/tests",
        "/downloads",
        "/analytics",
        "/resources",
        "/settings",
    ]:
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/login")


def test_dashboard_template_uses_route_links(auth_client):
    response = auth_client.get("/dashboard")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'href="/dashboard"' in body
    assert 'href="/downloads"' in body
    assert 'href="#downloads"' not in body


def test_login_form_redirects_to_dashboard_on_success(client):
    _admin_login(client)
    client.post("/api/register", json={"username": "alice", "password": "secret"})
    client.post("/api/admin/logout")

    response = client.post(
        "/login",
        data={"username": "alice", "password": "secret"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_login_logout_flow(client):
    _admin_login(client)
    client.post("/api/register", json={"username": "alice", "password": "secret"})
    client.post("/api/logout")

    bad = client.post("/api/login", json={"username": "alice", "password": "wrong"})
    assert bad.status_code == 401

    good = client.post("/api/login", json={"username": "alice", "password": "secret"})
    assert good.status_code == 200

    logout = client.post("/api/logout")
    assert logout.status_code == 200
    assert client.get("/api/me").get_json()["user"] is None


def test_protected_routes_require_auth(client):
    for path, method in [
        ("/api/bootstrap", client.get),
        ("/api/progress", client.get),
        ("/api/settings", lambda p: client.put(p, json={})),
        ("/api/tasks", client.get),
    ]:
        response = method(path)
        assert response.status_code == 401


def test_bootstrap_returns_only_current_user_tasks(auth_client, app):
    with app.app_context():
        alice = User.query.filter_by(username="alice").first()
        bob = _create_user("bob", "secret2")
        _create_task(alice.id, title="Alice task")
        _create_task(bob.id, title="Bob task")

    response = auth_client.get("/api/bootstrap")
    assert response.status_code == 200
    tasks = response.get_json()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Alice task"


def test_get_tasks_returns_only_current_user_tasks(auth_client, app):
    with app.app_context():
        alice = User.query.filter_by(username="alice").first()
        bob = _create_user("bob", "secret2")
        _create_task(alice.id, title="Alice task")
        _create_task(bob.id, title="Bob task")

    response = auth_client.get("/api/tasks")
    assert response.status_code == 200
    payload = response.get_json()
    assert "tasks" in payload
    assert len(payload["tasks"]) == 1
    assert payload["tasks"][0]["title"] == "Alice task"


def test_create_task_happy_path_with_optional_fields(auth_client, app):
    response = auth_client.post(
        "/api/tasks",
        json={
            "title": "  Work examples  ",
            "unit": "Linear Algebra",
            "topic": "Eigenvalues",
            "priority": "High",
            "due_date": "2030-05-01",
            "notes": "  Review solved problems.  ",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["title"] == "Work examples"

    with app.app_context():
        task = db.session.get(Task, payload["id"])
        assert task is not None
        assert task.topic == "Eigenvalues"


def test_create_task_validation_errors(auth_client):
    response = auth_client.post(
        "/api/tasks",
        json={
            "title": "   ",
            "unit": "",
            "topic": "Topic",
            "priority": "Urgent",
            "due_date": "2030/01/01",
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "Validation failed"
    assert payload["details"]["title"] == "title cannot be blank"
    assert payload["details"]["unit"] == "unit cannot be blank"
    assert "priority" in payload["details"]
    assert "due_date" in payload["details"]


def test_update_task_accepts_additional_fields(auth_client, app):
    with app.app_context():
        alice = User.query.filter_by(username="alice").first()
        task_id = _create_task(alice.id).id

    response = auth_client.patch(
        f"/api/tasks/{task_id}",
        json={
            "title": "Updated title",
            "unit": "Numerical Analysis",
            "topic": "Errors",
            "completed": True,
            "due_date": "2035-01-10",
            "notes": "updated",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["title"] == "Updated title"
    assert data["completed"] is True


def test_patch_task_validation_errors(auth_client, app):
    with app.app_context():
        alice = User.query.filter_by(username="alice").first()
        task_id = _create_task(alice.id).id

    response = auth_client.patch(
        f"/api/tasks/{task_id}", json={"completed": "yes", "due_date": "invalid"}
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "Validation failed"
    assert payload["details"]["completed"] == "completed must be a boolean"
    assert "due_date" in payload["details"]


def test_update_delete_cannot_access_other_users_task(auth_client, app):
    with app.app_context():
        bob = _create_user("bob", "secret2")
        bob_task_id = _create_task(bob.id).id

    patch_response = auth_client.patch(
        f"/api/tasks/{bob_task_id}", json={"completed": True}
    )
    assert patch_response.status_code == 404
    assert patch_response.get_json()["error"] == "Task not found"

    delete_response = auth_client.delete(f"/api/tasks/{bob_task_id}")
    assert delete_response.status_code == 404
    assert delete_response.get_json()["error"] == "Task not found"


def test_update_settings_happy_path(auth_client, app):
    response = auth_client.put(
        "/api/settings",
        json={"daily_goal": 7, "theme": "light", "exam_date": "2031-10-12"},
    )
    assert response.status_code == 200

    with app.app_context():
        alice = User.query.filter_by(username="alice").first()
        setting = get_or_create_settings(alice)
        assert setting.daily_goal == 7


def test_register_requires_username_and_password(client):
    _admin_login(client)
    missing_username = client.post("/api/register", json={"password": "secret"})
    assert missing_username.status_code == 400

    missing_password = client.post("/api/register", json={"username": "alice"})
    assert missing_password.status_code == 400


def test_login_requires_username_and_password(client):
    response = client.post("/api/login", json={"username": "alice"})
    assert response.status_code == 400


def test_update_settings_validation_errors(auth_client):
    response = auth_client.put(
        "/api/settings",
        json={"daily_goal": True, "theme": "   ", "exam_date": "2031/10/12"},
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"] == "Validation failed"
    assert payload["details"]["daily_goal"] == "daily_goal must be an integer"
    assert payload["details"]["theme"] == "theme cannot be blank"
    assert "exam_date" in payload["details"]


def test_progress_returns_user_specific_aggregates(auth_client, app):
    with app.app_context():
        alice = User.query.filter_by(username="alice").first()
        bob = _create_user("bob", "secret2")
        _create_task(alice.id, unit="Algebra", completed=True)
        _create_task(alice.id, unit="Algebra", completed=False)
        _create_task(bob.id, unit="Algebra", completed=True)

        setting = get_or_create_settings(alice)
        setting.exam_date = date.today() + timedelta(days=10)
        db.session.commit()

    response = auth_client.get("/api/progress")
    data = response.get_json()
    assert data["total"] == 2
    assert data["completed"] == 1
    assert data["days_left"] == 10


def test_progress_uses_unit_breakdown_helper(auth_client, monkeypatch):
    fake_breakdown = {"Custom": {"total": 99, "completed": 88}}
    calc_spy = Mock(return_value=fake_breakdown)
    monkeypatch.setattr(tracker_app, "calculate_unit_breakdown", calc_spy)

    response = auth_client.get("/api/progress")

    assert response.status_code == 200
    assert response.get_json()["unit_breakdown"] == fake_breakdown
    calc_spy.assert_called_once()


def test_register_requires_admin_auth(client):
    response = client.post(
        "/api/register", json={"username": "alice", "password": "secret"}
    )
    assert response.status_code == 403


def test_admin_session_login_logout_flow(client):
    assert client.get("/api/admin/session").get_json()["is_admin"] is False

    bad = _admin_login(client, password="wrong")
    assert bad.status_code == 401

    good = _admin_login(client)
    assert good.status_code == 200
    assert client.get("/api/admin/session").get_json()["is_admin"] is True

    logout = client.post("/api/admin/logout")
    assert logout.status_code == 200
    assert client.get("/api/admin/session").get_json()["is_admin"] is False


def test_dashboard_includes_server_side_context_values(auth_client):
    response = auth_client.get("/dashboard")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert 'Study Streak:' in body
    assert 'window.APP_CONFIG' in body
    assert 'countDays' in body


def test_study_session_persists_and_updates_totals(auth_client):
    response = auth_client.post("/api/study-session", json={"duration_seconds": 1800})

    assert response.status_code == 201
    data = response.get_json()
    assert data["today_hours"] == 0.5
    assert data["week_hours"] >= 0.5


def test_daily_routine_toggle_and_progress(auth_client):
    response = auth_client.get("/api/daily-routine")
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["tasks"]) >= 1

    task_name = payload["tasks"][0]["task_name"]
    update = auth_client.post(
        "/api/daily-routine", json={"task_name": task_name, "completed": True}
    )
    assert update.status_code == 200
    assert update.get_json()["completed_percent"] > 0


def test_syllabus_progress_endpoint_and_score_page(auth_client):
    initial = auth_client.get("/api/syllabus-progress")
    assert initial.status_code == 200
    grouped = initial.get_json()["grouped_topics"]
    first_subject = next(iter(grouped))
    first_topic = grouped[first_subject][0]

    update = auth_client.post(
        "/api/syllabus-progress",
        json={
            "topic_id": first_topic["topic_id"],
            "field": "theory_completed",
            "value": True,
        },
    )
    assert update.status_code == 200

    score_page = auth_client.get("/score-predictor")
    assert score_page.status_code == 200
    assert "Predicted Score" in score_page.get_data(as_text=True)


def test_score_predictor_uses_weighted_baseline(auth_client, app):
    response = auth_client.get("/score-predictor")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Final Predicted Score / 200" in body
    assert ">20<" in body
    assert "Needs major improvement" in body


def test_score_predictor_reaches_jrf_category_with_full_progress(auth_client, app):
    from app import SyllabusTopic, User, UserSyllabusProgress

    with app.app_context():
        user = User.query.filter_by(username="alice").first()
        assert user is not None
        for topic in SyllabusTopic.query.all():
            db.session.add(
                UserSyllabusProgress(
                    user_id=user.id,
                    topic_id=topic.id,
                    theory_completed=True,
                    pyq_30_done=True,
                    revision_1_done=True,
                    revision_2_done=True,
                )
            )
        db.session.commit()

    response = auth_client.get("/score-predictor")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "200.0" in body or "200" in body
    assert "Strong JRF potential" in body
