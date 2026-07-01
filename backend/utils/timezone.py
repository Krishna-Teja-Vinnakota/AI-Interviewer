"""Timezone utilities for IST handling."""
from datetime import datetime, time
from typing import Optional
import pytz
from core.config import settings


IST = pytz.timezone(settings.TIMEZONE)
UTC = pytz.UTC


def get_ist_now() -> datetime:
    """Get current time in IST."""
    return datetime.now(IST)


def convert_to_ist(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to IST."""
    if utc_dt.tzinfo is None:
        utc_dt = UTC.localize(utc_dt)
    return utc_dt.astimezone(IST)


def convert_to_utc(ist_dt: datetime) -> datetime:
    """Convert IST datetime to UTC."""
    if ist_dt.tzinfo is None:
        ist_dt = IST.localize(ist_dt)
    return ist_dt.astimezone(UTC)


def is_within_interview_hours(dt: datetime) -> bool:
    """Check if datetime is within interview hours (10 AM - 7 PM IST)."""
    ist_dt = convert_to_ist(dt) if dt.tzinfo else IST.localize(dt)
    hour = ist_dt.hour
    return 10 <= hour < 19  # 10 AM to 7 PM (19:00)


def get_next_available_slot(start_time: Optional[datetime] = None) -> datetime:
    """Get next available interview slot within 10 AM - 7 PM IST."""
    if start_time is None:
        start_time = get_ist_now()
    else:
        start_time = convert_to_ist(start_time)
    
    # If before 10 AM, set to 10 AM today
    if start_time.hour < 10:
        start_time = start_time.replace(hour=10, minute=0, second=0, microsecond=0)
    # If after 7 PM, set to 10 AM next day
    elif start_time.hour >= 19:
        from datetime import timedelta
        start_time = (start_time + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    
    return start_time
