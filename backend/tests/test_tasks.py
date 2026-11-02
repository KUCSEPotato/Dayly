from datetime import UTC, datetime

import pytest

from app.models import Task


def create(client, **changes):
    payload = {"title": "FastAPI 공부", "scheduled_date": "2026-11-02", **changes}
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_list_and_persist_in_a_new_database_session(client, database):
    task = create(client, title="  FastAPI 공부  ", description="Router 이해하기")
    assert task["title"] == "FastAPI 공부"
    assert task["description"] == "Router 이해하기"
    assert task["is_completed"] is False
    assert task["completed_at"] is None
    for field in ("created_at", "updated_at"):
        assert datetime.fromisoformat(task[field].replace("Z", "+00:00")).utcoffset().total_seconds() == 0
    assert client.get("/api/tasks", params={"date": "2026-11-02"}).json() == [task]
    assert client.get("/api/tasks", params={"date": "2026-11-03"}).json() == []
    # A new Session reads the saved row, proving this isn't only in-memory API state.
    with database() as session:
        assert session.get(Task, task["id"]).title == "FastAPI 공부"


def test_update_move_and_clear_description(client):
    task = create(client, description="설명")
    response = client.patch(f"/api/tasks/{task['id']}", json={
        "title": "수정한 제목", "description": None, "scheduled_date": "2026-11-05",
    })
    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "수정한 제목"
    assert updated["description"] is None
    assert updated["created_at"] == task["created_at"]
    assert updated["updated_at"] >= task["updated_at"]
    assert client.get("/api/tasks?date=2026-11-02").json() == []
    assert client.get("/api/tasks?date=2026-11-05").json()[0]["id"] == task["id"]
    days = client.get("/api/calendar?year=2026&month=11").json()["days"]
    assert days[1]["total"] == 0
    assert days[4]["total"] == 1
    assert client.get("/api/stats/weekly").json()["total"] == 0


def test_completion_toggle_is_idempotent_and_updates_statistics(client):
    task = create(client)
    path = f"/api/tasks/{task['id']}"
    completed = client.patch(path, json={"is_completed": True}).json()
    assert completed["is_completed"] is True
    assert datetime.fromisoformat(completed["completed_at"].replace("Z", "+00:00")).tzinfo == UTC
    repeated = client.patch(path, json={"is_completed": True}).json()
    assert repeated["completed_at"] == completed["completed_at"]
    assert client.get("/api/stats/daily?date=2026-11-02").json()["completion_rate"] == 100
    assert client.get("/api/stats/weekly").json()["completion_rate"] == 100
    undone = client.patch(path, json={"is_completed": False}).json()
    assert undone["is_completed"] is False
    assert undone["completed_at"] is None
    assert client.get("/api/stats/weekly").json()["completion_rate"] == 0


def test_delete_removes_row_and_aggregates(client, database):
    task = create(client)
    response = client.delete(f"/api/tasks/{task['id']}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/api/tasks?date=2026-11-02").json() == []
    assert client.get("/api/stats/weekly").json()["total"] == 0
    assert client.get("/api/stats/daily?date=2026-11-02").json()["completion_rate"] is None
    with database() as session:
        assert session.get(Task, task["id"]) is None


@pytest.mark.parametrize("payload", [
    {"title": ""}, {"title": " \t\n "}, {"title": "x" * 201},
    {"description": "x" * 5001}, {"scheduled_date": "2026-02-30"},
    {"scheduled_date": None}, {"is_completed": True}, {"unknown": "field"},
])
def test_create_rejects_invalid_input(client, payload):
    response = client.post("/api/tasks", json={"title": "할 일", "scheduled_date": "2026-11-02", **payload})
    assert response.status_code == 422
    assert client.get("/api/tasks?date=2026-11-02").json() == []


@pytest.mark.parametrize("payload", [
    {}, {"title": None}, {"title": "  "}, {"scheduled_date": None},
    {"is_completed": None}, {"completed_at": "2026-11-02T00:00:00Z"},
])
def test_patch_rejects_invalid_input_without_changing_task(client, payload):
    task = create(client)
    assert client.patch(f"/api/tasks/{task['id']}", json=payload).status_code == 422
    assert client.get("/api/tasks?date=2026-11-02").json() == [task]


def test_nonexistent_task(client):
    assert client.patch("/api/tasks/999", json={"title": "없음"}).status_code == 404
    assert client.delete("/api/tasks/999").status_code == 404
    assert client.delete("/api/tasks/0").status_code == 422


def test_future_tasks_are_accessible(client):
    task = create(client, scheduled_date="2028-02-29")
    assert client.get("/api/tasks?date=2028-02-29").json()[0]["id"] == task["id"]
    assert client.get("/api/stats/daily?date=2028-02-29").status_code == 200
    assert client.patch(f"/api/tasks/{task['id']}", json={"title": "미래 일정"}).status_code == 200
