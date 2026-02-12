from datetime import datetime
from zoneinfo import ZoneInfo

now_Berlin_forced = None


def now_Berlin() -> datetime:
    return (
        datetime.now(ZoneInfo("Europe/Berlin"))
        if now_Berlin_forced is None
        else now_Berlin_forced
    )


def set_now_Berlin_forced(x):
    global now_Berlin_forced
    now_Berlin_forced = x
