"""Google Calendar event parsing and meeting URL extraction."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

# Ordered by specificity — first match wins
_URL_PATTERNS = [
    # Zoom
    (re.compile(r"https?://[\w.-]*zoom\.us/[jw]/[\w?=&]+", re.I), "zoom"),
    # Google Meet
    (re.compile(r"https?://meet\.google\.com/[a-z]{3}-[a-z]{4}-[a-z]{3}", re.I), "google_meet"),
    # Microsoft Teams
    (re.compile(r"https?://teams\.microsoft\.com/l/meetup-join/[^\s\"'<>]+", re.I), "teams"),
    # Generic video conference fallback
    (re.compile(r"https?://[\w.-]+/[^\s\"'<>]*(?:meeting|call|join|conference)[^\s\"'<>]*", re.I), "other"),
]

# iCalendar RRULE recurrence indicators
_RECURRING_KEYS = {"RRULE", "RDATE", "EXRULE"}


@dataclass
class ParsedEvent:
    event_id: str
    title: str
    start_time: datetime
    end_time: datetime
    meeting_url: str | None
    platform: str | None
    is_recurring: bool
    recurrence_id: str | None       # iCal UID for recurring series
    attendee_emails: list[str]
    organizer_email: str | None
    description: str


def extract_meeting_url(text: str) -> tuple[str | None, str | None]:
    """Return (url, platform) from any text blob (description, location, etc.)."""
    for pattern, platform in _URL_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(0), platform
    return None, None


def parse_calendar_event(event: dict) -> ParsedEvent:
    """
    Parse a Google Calendar API event dict into a structured ParsedEvent.
    Handles both regular and recurring events.
    """
    event_id: str = event.get("id", "")
    title: str = event.get("summary", "Untitled Meeting")
    description: str = event.get("description", "") or ""
    location: str = event.get("location", "") or ""

    # Start / end times (prefer dateTime over date)
    start_raw = event.get("start", {})
    end_raw = event.get("end", {})
    start_time = _parse_dt(start_raw.get("dateTime") or start_raw.get("date", ""))
    end_time = _parse_dt(end_raw.get("dateTime") or end_raw.get("date", ""))

    # Extract meeting URL — check description, location, conferenceData
    meeting_url, platform = None, None

    conf = event.get("conferenceData", {})
    for ep in conf.get("entryPoints", []):
        if ep.get("entryPointType") == "video":
            meeting_url = ep.get("uri")
            platform = _platform_from_conf(conf.get("conferenceSolution", {}).get("key", {}).get("type", ""))
            break

    if not meeting_url:
        meeting_url, platform = extract_meeting_url(description + " " + location)

    # Recurrence
    recurrence = event.get("recurrence", [])
    is_recurring = bool(recurrence) or bool(event.get("recurringEventId"))
    recurrence_id: str | None = event.get("recurringEventId") or (event_id if is_recurring else None)

    # Attendees
    attendees = event.get("attendees", [])
    attendee_emails = [a["email"] for a in attendees if a.get("email") and not a.get("self")]
    organizer = event.get("organizer", {})
    organizer_email = organizer.get("email")

    return ParsedEvent(
        event_id=event_id,
        title=title,
        start_time=start_time,
        end_time=end_time,
        meeting_url=meeting_url,
        platform=platform,
        is_recurring=is_recurring,
        recurrence_id=recurrence_id,
        attendee_emails=attendee_emails,
        organizer_email=organizer_email,
        description=description,
    )


def _parse_dt(raw: str) -> datetime:
    if not raw:
        return datetime.utcnow()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return datetime.utcnow()


def _platform_from_conf(conf_type: str) -> str | None:
    mapping = {
        "hangoutsMeet": "google_meet",
        "addOn": None,
    }
    return mapping.get(conf_type)
