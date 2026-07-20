from datetime import datetime

_current_day = ""
_proactive_count = 0


def _today() -> str:
    return datetime.now().date().isoformat()


def _reset_if_needed() -> None:
    global _current_day, _proactive_count
    today = _today()
    if _current_day != today:
        _current_day = today
        _proactive_count = 0


def get_proactive_daily_count() -> int:
    _reset_if_needed()
    return _proactive_count


def increment_proactive_daily_count() -> int:
    global _proactive_count
    _reset_if_needed()
    _proactive_count += 1
    return _proactive_count
