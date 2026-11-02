from datetime import date, timedelta

from app.core.errors import DomainError


def ensure_accessible(day: date, today: date) -> None:
    # Keep historical data in the DB; only aggregate calendar queries may read older days.
    if day < today - timedelta(days=6):
        raise DomainError("history_restricted", "7일보다 오래된 기록은 달력의 요약만 조회할 수 있습니다.")
