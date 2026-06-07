import uuid
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


def _new_event_id() -> str:
    return str(uuid.uuid4())

def _now() -> datetime:
    return datetime.utcnow()


# ── Base ───────────────────────────────────────────────────────────────────

class EventBase(BaseModel):
    """
    Every event carries these envelope fields.
    Consumers use event_id for idempotency and event_type for routing.
    """
    event_id:   str      = Field(default_factory=_new_event_id)
    event_type: str
    occurred_at: datetime = Field(default_factory=_now)
    version:    int      = 1        # bump when payload shape changes


# ── Payloads ───────────────────────────────────────────────────────────────

class TaskCreatedPayload(BaseModel):
    task_id:      str
    project_id:   str
    workspace_id: str
    title:        str
    status:       str
    priority:     str
    created_by:   str
    assignee_id:  Optional[str] = None
    due_date:     Optional[datetime] = None


class TaskCompletedPayload(BaseModel):
    task_id:      str
    project_id:   str
    workspace_id: str
    title:        str
    completed_by: str           # user who triggered the status → done
    completed_at: datetime
    assignee_id:  Optional[str] = None


class TaskUpdatedPayload(BaseModel):
    task_id:      str
    project_id:   str
    workspace_id: str
    updated_by:   str
    changes:      dict[str, Any]    # {"field": {"old": x, "new": y}}


# ── Concrete events ────────────────────────────────────────────────────────

class TaskCreatedEvent(EventBase):
    event_type: str = "task.created"
    payload: TaskCreatedPayload


class TaskCompletedEvent(EventBase):
    event_type: str = "task.completed"
    payload: TaskCompletedPayload


class TaskUpdatedEvent(EventBase):
    event_type: str = "task.updated"
    payload: TaskUpdatedPayload