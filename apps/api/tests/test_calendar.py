"""Tests for calendar event parsing and URL extraction."""
import pytest
from datetime import datetime, timezone

from app.services.calendar import extract_meeting_url, parse_calendar_event


# ---------------------------------------------------------------------------
# URL extraction
# ---------------------------------------------------------------------------

def test_extract_zoom_url():
    text = "Join via https://us02web.zoom.us/j/123456789?pwd=abc123 — see you there!"
    url, platform = extract_meeting_url(text)
    assert url is not None
    assert "zoom.us" in url
    assert platform == "zoom"


def test_extract_google_meet():
    text = "Meeting link: https://meet.google.com/abc-defg-hij"
    url, platform = extract_meeting_url(text)
    assert url is not None
    assert "meet.google.com" in url
    assert platform == "google_meet"


def test_extract_teams_url():
    url_str = "https://teams.microsoft.com/l/meetup-join/19%3ameeting_abc123/0?context=xyz"
    url, platform = extract_meeting_url(f"Join: {url_str}")
    assert url is not None
    assert platform == "teams"


def test_extract_no_url():
    url, platform = extract_meeting_url("No meeting link here — just text.")
    assert url is None
    assert platform is None


# ---------------------------------------------------------------------------
# Event parsing
# ---------------------------------------------------------------------------

SAMPLE_EVENT = {
    "id": "evt_abc123",
    "summary": "Q3 Planning",
    "description": "Agenda:\n1. OKRs\n\nJoin: https://meet.google.com/xyz-abcd-efg",
    "location": "",
    "start": {"dateTime": "2026-06-01T10:00:00Z"},
    "end": {"dateTime": "2026-06-01T11:00:00Z"},
    "attendees": [
        {"email": "alice@example.com"},
        {"email": "bob@example.com", "self": True},
    ],
    "organizer": {"email": "alice@example.com"},
    "recurrence": [],
}

RECURRING_EVENT = {
    **SAMPLE_EVENT,
    "id": "evt_recurring_20260601",
    "recurringEventId": "evt_base_recurring",
    "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=MO"],
}


def test_parse_basic_event():
    parsed = parse_calendar_event(SAMPLE_EVENT)
    assert parsed.event_id == "evt_abc123"
    assert parsed.title == "Q3 Planning"
    assert parsed.meeting_url is not None
    assert "meet.google.com" in parsed.meeting_url
    assert parsed.platform == "google_meet"
    assert parsed.is_recurring is False
    assert "alice@example.com" in parsed.attendee_emails
    # bob@example.com has self=True → excluded from attendee_emails
    assert "bob@example.com" not in parsed.attendee_emails
    assert parsed.organizer_email == "alice@example.com"


def test_parse_recurring_event():
    parsed = parse_calendar_event(RECURRING_EVENT)
    assert parsed.is_recurring is True
    assert parsed.recurrence_id == "evt_base_recurring"


def test_parse_event_conference_data():
    event_with_conf = {
        **SAMPLE_EVENT,
        "description": "No URL here",
        "conferenceData": {
            "entryPoints": [
                {
                    "entryPointType": "video",
                    "uri": "https://meet.google.com/conf-data-url",
                }
            ],
            "conferenceSolution": {
                "key": {"type": "hangoutsMeet"}
            },
        },
    }
    parsed = parse_calendar_event(event_with_conf)
    assert parsed.meeting_url == "https://meet.google.com/conf-data-url"
    assert parsed.platform == "google_meet"


def test_parse_event_no_url():
    event = {**SAMPLE_EVENT, "description": "No link here", "location": ""}
    parsed = parse_calendar_event(event)
    assert parsed.meeting_url is None
    assert parsed.platform is None


def test_parse_event_times():
    parsed = parse_calendar_event(SAMPLE_EVENT)
    assert isinstance(parsed.start_time, datetime)
    assert isinstance(parsed.end_time, datetime)
    assert parsed.start_time < parsed.end_time
