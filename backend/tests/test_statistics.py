from datetime import UTC, date, datetime, timedelta

import pytest

from app.models import Task
from app.services.statistics import completion_rate


def seed(database, day, total, completed):
    with database() as session:
        tasks = [Task(title=f"할 일 {index}", scheduled_date=date.fromisoformat(day),
                      is_completed=index < completed,
                      completed_at=datetime(2026, 11, 1, tzinfo=UTC) if index < completed else None)
                 for index in range(total)]
        session.add_all(tasks)
        session.commit()
        return [task.id for task in tasks]


def test_seven_of_ten_is_seventy_percent(client, database):
    seed(database, "2026-11-02", 10, 7)
    assert client.get("/api/stats/daily?date=2026-11-02").json() == {
        "date": "2026-11-02", "total": 10, "completed": 7, "incomplete": 3, "completion_rate": 70.0,
    }


def test_weighted_weekly_rate_and_inclusive_boundaries(client, database):
    seed(database, "2026-10-26", 20, 20)  # excluded: seven days ago
    seed(database, "2026-10-27", 1, 1)    # included: first day
    seed(database, "2026-11-02", 9, 0)    # included: today
    seed(database, "2026-11-03", 30, 30)  # excluded: future
    stats = client.get("/api/stats/weekly").json()
    assert stats["start_date"] == "2026-10-27"
    assert stats["end_date"] == "2026-11-02"
    assert stats["total"] == 10
    assert stats["completed"] == 1
    assert stats["incomplete"] == 9
    assert stats["completion_rate"] == 10  # (1/10), rather than mean(100%, 0%)
    assert len(stats["days"]) == 7
    assert stats["days"][1]["completion_rate"] is None
    assert stats["days"][0]["date"] == "2026-10-27"
    assert stats["days"][-1]["date"] == "2026-11-02"


def test_empty_statistics_use_null(client):
    assert client.get("/api/stats/daily?date=2026-11-02").json()["completion_rate"] is None
    stats = client.get("/api/stats/weekly").json()
    assert stats["completion_rate"] is None
    assert all(day["total"] == 0 and day["completion_rate"] is None for day in stats["days"])
    assert completion_rate(0, 0) is None


def test_old_details_restricted_but_calendar_and_data_retained(client, database):
    task_id = seed(database, "2026-10-26", 1, 1)[0]
    for path in ("/api/tasks?date=2026-10-26", "/api/stats/daily?date=2026-10-26"):
        response = client.get(path)
        assert response.status_code == 403
        assert response.json()["code"] == "history_restricted"
    assert client.patch(f"/api/tasks/{task_id}", json={"scheduled_date": "2026-11-02"}).status_code == 403
    assert client.delete(f"/api/tasks/{task_id}").status_code == 403
    assert client.post("/api/tasks", json={"title": "과거", "scheduled_date": "2026-10-26"}).status_code == 403
    days = client.get("/api/calendar?year=2026&month=10").json()["days"]
    assert len(days) == 31
    assert days[25]["total"] == 1
    assert days[25]["completed"] == 1
    with database() as session:
        assert session.get(Task, task_id) is not None
    assert client.get("/api/tasks?date=2026-10-27").status_code == 200


def test_moving_task_to_restricted_date_is_rejected(client, database):
    task_id = seed(database, "2026-11-02", 1, 0)[0]
    assert client.patch(f"/api/tasks/{task_id}", json={"scheduled_date": "2026-10-26"}).status_code == 403
    assert len(client.get("/api/tasks?date=2026-11-02").json()) == 1


@pytest.mark.parametrize("query,days", [("year=2028&month=2", 29), ("year=2027&month=2", 28), ("year=2026&month=12", 31)])
def test_calendar_month_lengths(client, query, days):
    assert len(client.get(f"/api/calendar?{query}").json()["days"]) == days


@pytest.mark.parametrize("path", [
    "/api/calendar?year=2026&month=0", "/api/calendar?year=2026&month=13",
    "/api/calendar?year=0&month=1", "/api/tasks?date=not-a-date",
    "/api/stats/daily?date=2026-02-30", "/api/tasks",
])
def test_invalid_queries(client, path):
    assert client.get(path).status_code == 422


def test_seoul_today_changes_at_korean_midnight(monkeypatch):
    import app.core.clock as clock

    class FrozenDateTime(datetime):
        instant = datetime(2026, 11, 1, 14, 59, 59, tzinfo=UTC)

        @classmethod
        def now(cls, tz=None):
            return cls.instant.astimezone(tz)

    monkeypatch.setattr(clock, "datetime", FrozenDateTime)
    assert clock.seoul_today() == date(2026, 11, 1)
    FrozenDateTime.instant += timedelta(seconds=1)
    assert clock.seoul_today() == date(2026, 11, 2)
