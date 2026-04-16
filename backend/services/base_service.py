from datetime import date, datetime
from typing import Any

from fastapi import HTTPException

from backend.models import _coerce_date_to_datetime


class BaseService:
    """Base class with common service utilities."""

    @staticmethod
    def raise_bad_request(detail: str) -> None:
        raise HTTPException(status_code=400, detail=detail)

    @staticmethod
    def raise_forbidden(detail: str) -> None:
        raise HTTPException(status_code=403, detail=detail)

    @staticmethod
    def raise_not_found(detail: str) -> None:
        raise HTTPException(status_code=404, detail=detail)

    @staticmethod
    def raise_conflict(detail: str) -> None:
        raise HTTPException(status_code=409, detail=detail)

    @staticmethod
    def coerce_datetime(value: Any) -> datetime:
        return _coerce_date_to_datetime(value)

    @staticmethod
    def parse_date_param(date_str: str) -> datetime:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid date format '{date_str}'. Use YYYY-MM-DD.")

    @staticmethod
    def ensure_not_future(work_date: datetime, detail: str) -> None:
        today_midnight = datetime.combine(date.today(), datetime.min.time())
        if work_date > today_midnight:
            raise HTTPException(status_code=400, detail=detail)
