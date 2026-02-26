from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import Mock

import pytest

import app as tracker_app
from app import Task, db, get_or_create_settings


def _create_task(*, title="Read chapter", unit="Algebra", topic="Groups", **overrides):
    task = Task(title=title, unit=unit, topic=topic, **overrides)
    db.session.add(task)
    db.session.commit()
    return task


def test_index_route_renders_template(client, monkeypatch):
    render_stub = Mock(return_value="rendered-index")
    monkeypatch.setattr(tracker_app, "render_template", render_stub)

    response = client.get("/")

    assert response.status_code == 200
    assert response.get_data(as_text=True) == "rendered-index"
    render_stub.assert_called_once_with("index.html", syllabus=tracker_app.SYLLABUS)


def test_bootstrap_returns_settings_syllabus_and_tasks_in_desc_created_order(client, app):
    with app.app_context():
        older_id = _create_task(title="Old task").id
        newer_id = _create_task(title="New task").id

    response = client.get("/api/bootstrap")

    assert response.status_code == 200
    data = response.get_json()
    assert data["settings"]["daily_goal"] == 3
    assert data["settings"]["theme"] == "dark"
    assert data["syllabus"] == tracker_app.SYLLABUS
    returned_ids = [task["id"] for task in data["tasks"]]
    assert returned_ids.index(newer_id) < returned_ids.index(older_id)


def test_create_task_happy_path_with_optional_fields(client, app):
    response = client.post(
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
    assert payload["notes"] == "Review solved problems."
    assert payload["due_date"] == "2030-05-01"
    assert payload["priority"] == "High"

    with app.app_context():
        task = db.session.get(Task, payload["id"])
        assert task is not None
        assert task.topic == "Eigenvalues"


def test_create_task_uses_defaults_when_optional_fields_not_provided(client):
    response = client.post(
        "/api/tasks",
        json={"title": "Write summary", "unit": "Complex Analysis", "topic": "Residues"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert payload["priority"] == "Medium"
    assert payload["due_date"] is None
    assert payload["notes"] == ""


@pytest.mark.parametrize(
    "bad_payload,missing_field",
    [
        ({"unit": "Algebra", "topic": "Groups"}, "title"),
        ({"title": "Missing unit", "topic": "Groups"}, "unit"),
        ({"title": "Missing topic", "unit": "Algebra"}, "topic"),
    ],
)
def test_create_task_missing_required_fields_raise_key_error(client, bad_payload, missing_field):
    with pytest.raises(KeyError, match=missing_field):
        client.post("/api/tasks", json=bad_payload)


def test_create_task_invalid_due_date_raises_value_error(client):
    with pytest.raises(ValueError, match="does not match format"):
        client.post(
            "/api/tasks",
            json={
                "title": "Invalid date",
                "unit": "Algebra",
                "topic": "Groups",
                "due_date": "05/01/2030",
            },
        )


def test_update_task_updates_only_supported_fields(client, app):
    with app.app_context():
        task_id = _create_task(priority="Low").id

    response = client.patch(
        f"/api/tasks/{task_id}",
        json={"completed": True, "priority": "High", "title": "Ignored by PATCH"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["completed"] is True
    assert payload["priority"] == "High"

    with app.app_context():
        refreshed = db.session.get(Task, task_id)
        assert refreshed.title == "Read chapter"


def test_update_task_unknown_id_returns_404(client):
    response = client.patch("/api/tasks/99999", json={"completed": True})
    assert response.status_code == 404


def test_delete_task_happy_path(client, app):
    with app.app_context():
        task_id = _create_task().id

    response = client.delete(f"/api/tasks/{task_id}")

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}

    with app.app_context():
        assert db.session.get(Task, task_id) is None


def test_delete_task_unknown_id_returns_404(client):
    response = client.delete("/api/tasks/123456")
    assert response.status_code == 404


def test_update_settings_happy_path(client, app):
    response = client.put(
        "/api/settings",
        json={"daily_goal": 7, "theme": "light", "exam_date": "2031-10-12"},
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data == {"daily_goal": 7, "theme": "light", "exam_date": "2031-10-12"}

    with app.app_context():
        setting = get_or_create_settings()
        assert setting.daily_goal == 7
        assert setting.theme == "light"


def test_update_settings_allows_partial_updates(client, app):
    with app.app_context():
        setting = get_or_create_settings()
        setting.daily_goal = 5
        db.session.commit()

    response = client.put("/api/settings", json={"theme": "solarized"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["daily_goal"] == 5
    assert data["theme"] == "solarized"


def test_update_settings_invalid_date_raises_value_error(client):
    with pytest.raises(ValueError, match="does not match format"):
        client.put("/api/settings", json={"exam_date": "31-12-2030"})


def test_update_settings_invalid_daily_goal_type_raises_value_error(client):
    with pytest.raises(ValueError, match="invalid literal for int"):
        client.put("/api/settings", json={"daily_goal": "abc"})


def test_progress_returns_aggregates_and_countdown(client, app):
    with app.app_context():
        _create_task(unit="Algebra", completed=True)
        _create_task(unit="Algebra", completed=False)
        _create_task(unit="New Unit", completed=True)
        setting = get_or_create_settings()
        setting.exam_date = date.today() + timedelta(days=10)
        db.session.commit()

    response = client.get("/api/progress")

    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 3
    assert data["completed"] == 2
    assert data["pending"] == 1
    assert data["completion_rate"] == pytest.approx(66.7)
    assert data["days_left"] == 10
    assert data["unit_breakdown"]["Algebra"] == {"total": 2, "completed": 1}
    assert data["unit_breakdown"]["New Unit"] == {"total": 1, "completed": 1}


def test_progress_when_no_tasks_returns_zeroed_metrics_and_no_countdown(client):
    response = client.get("/api/progress")

    assert response.status_code == 200
    data = response.get_json()
    assert data["total"] == 0
    assert data["completed"] == 0
    assert data["pending"] == 0
    assert data["completion_rate"] == 0
    assert data["days_left"] is None


def test_progress_uses_unit_breakdown_helper(client, monkeypatch):
    fake_breakdown = {"Custom": {"total": 99, "completed": 88}}
    calc_spy = Mock(return_value=fake_breakdown)
    monkeypatch.setattr(tracker_app, "calculate_unit_breakdown", calc_spy)

    response = client.get("/api/progress")

    assert response.status_code == 200
    assert response.get_json()["unit_breakdown"] == fake_breakdown
    calc_spy.assert_called_once()
