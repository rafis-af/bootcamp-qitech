from datetime import date, datetime, time, timedelta
from typing import Tuple
from zoneinfo import ZoneInfo

from errors import InvalidDate

SAO_PAULO = ZoneInfo("America/Sao_Paulo")


def now() -> datetime:
    return datetime.now(SAO_PAULO)


def today() -> date:
    return now().date()


def day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=SAO_PAULO)


def today_range() -> Tuple[datetime, datetime]:
    start = day_start(today())
    return start, start + timedelta(days=1)


def current_month_range() -> Tuple[datetime, datetime]:
    first_day = today().replace(day=1)

    if first_day.month == 12:
        next_month_first_day = first_day.replace(year=first_day.year + 1, month=1)
    else:
        next_month_first_day = first_day.replace(month=first_day.month + 1)

    return day_start(first_day), day_start(next_month_first_day)


def day_end(day: date) -> datetime:
    return day_start(day + timedelta(days=1))


def parse_date(field: str, raw_date: str) -> date:
    try:
        return date.fromisoformat(raw_date)
    except ValueError:
        raise InvalidDate(field, raw_date)


def to_local_isoformat(moment: datetime) -> str:
    return moment.astimezone(SAO_PAULO).isoformat()
