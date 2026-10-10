from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.campaign_automation import _next_schedule_time


def test_campaign_delays_are_cumulative_between_emails():
    campaign = SimpleNamespace(
        sending_settings={
            "delay_min_minutes": 5,
            "delay_max_minutes": 5,
            "start_time": "00:00",
            "end_time": "23:59",
        }
    )
    first = datetime.now(timezone.utc).replace(second=0, microsecond=0)

    second = _next_schedule_time(campaign, previous_time=first)
    third = _next_schedule_time(campaign, previous_time=second)

    assert second == first + timedelta(minutes=5)
    assert third == second + timedelta(minutes=5)
