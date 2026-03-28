from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.auth import get_current_user
from app.config import settings
from app.models import User

router = APIRouter(prefix="/api/gcal", tags=["gcal"])

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
TOKEN_FILE = Path("gcal_token.json")


def _check_packages():
    try:
        import google.oauth2.credentials  # noqa
        import google_auth_oauthlib.flow  # noqa
        import googleapiclient.discovery  # noqa
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="Google packages missing. Run: pip install google-auth google-auth-oauthlib google-api-python-client",
        )


def _get_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if not TOKEN_FILE.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json())
        return creds if creds.valid else None
    except Exception:
        return None


def _get_flow():
    from google_auth_oauthlib.flow import Flow

    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uris": [settings.google_redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = settings.google_redirect_uri
    return flow


def _get_service():
    from googleapiclient.discovery import build

    creds = _get_credentials()
    if not creds:
        raise HTTPException(status_code=401, detail="Google Calendar not connected")
    return build("calendar", "v3", credentials=creds)


@router.get("/status")
def gcal_status(_: User = Depends(get_current_user)):
    if not settings.google_client_id or not settings.google_client_secret:
        return {"connected": False, "reason": "not_configured"}
    try:
        _check_packages()
    except HTTPException:
        return {"connected": False, "reason": "packages_missing"}
    creds = _get_credentials()
    return {"connected": creds is not None, "calendar_id": settings.google_calendar_id}


@router.get("/auth-url")
def gcal_auth_url(_: User = Depends(get_current_user)):
    _check_packages()
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=503, detail="GROCERY_GOOGLE_CLIENT_ID and GROCERY_GOOGLE_CLIENT_SECRET not set")
    if not settings.google_redirect_uri:
        raise HTTPException(status_code=503, detail="GROCERY_GOOGLE_REDIRECT_URI not set")
    flow = _get_flow()
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return {"url": auth_url}


@router.get("/callback")
def gcal_callback(code: str = Query(...), _: User = Depends(get_current_user)):
    _check_packages()
    flow = _get_flow()
    flow.fetch_token(code=code)
    TOKEN_FILE.write_text(flow.credentials.to_json())
    return RedirectResponse(url="/")


@router.get("/events")
def gcal_events(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(...),
    _: User = Depends(get_current_user),
):
    _check_packages()
    service = _get_service()

    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    time_min = f"{start.isoformat()}T00:00:00Z"
    time_max = f"{end.isoformat()}T00:00:00Z"

    result = service.events().list(
        calendarId=settings.google_calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy="startTime",
        maxResults=250,
    ).execute()

    events = []
    for e in result.get("items", []):
        start_info = e.get("start", {})
        is_all_day = "date" in start_info and "dateTime" not in start_info
        if is_all_day:
            event_date = start_info["date"]
            start_time = end_time = None
        else:
            dt_str = start_info.get("dateTime", "")
            event_date = dt_str[:10] if dt_str else None
            start_time = dt_str[11:16] if len(dt_str) >= 16 else None
            end_dt = e.get("end", {}).get("dateTime", "")
            end_time = end_dt[11:16] if len(end_dt) >= 16 else None

        events.append({
            "id": e["id"],
            "title": e.get("summary", "(no title)"),
            "date": event_date,
            "all_day": is_all_day,
            "start_time": start_time,
            "end_time": end_time,
        })

    return events


class GcalEventCreate(BaseModel):
    title: str
    date: str  # YYYY-MM-DD
    all_day: bool = True
    start_time: Optional[str] = None  # HH:MM
    end_time: Optional[str] = None    # HH:MM
    timezone: str = "Europe/Rome"


@router.post("/events")
def gcal_create_event(data: GcalEventCreate, _: User = Depends(get_current_user)):
    _check_packages()
    service = _get_service()

    if data.all_day:
        end_date = (date.fromisoformat(data.date) + timedelta(days=1)).isoformat()
        event_body = {
            "summary": data.title,
            "start": {"date": data.date},
            "end": {"date": end_date},
        }
    else:
        start_dt = f"{data.date}T{data.start_time or '09:00'}:00"
        end_dt = f"{data.date}T{data.end_time or '10:00'}:00"
        event_body = {
            "summary": data.title,
            "start": {"dateTime": start_dt, "timeZone": data.timezone},
            "end": {"dateTime": end_dt, "timeZone": data.timezone},
        }

    created = service.events().insert(
        calendarId=settings.google_calendar_id,
        body=event_body,
    ).execute()

    return {"id": created["id"], "title": created.get("summary")}


@router.delete("/events/{event_id}")
def gcal_delete_event(event_id: str, _: User = Depends(get_current_user)):
    _check_packages()
    service = _get_service()
    service.events().delete(
        calendarId=settings.google_calendar_id,
        eventId=event_id,
    ).execute()
    return {"ok": True}


@router.delete("/disconnect")
def gcal_disconnect(_: User = Depends(get_current_user)):
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
    return {"ok": True}
