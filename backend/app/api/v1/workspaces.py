from __future__ import annotations
import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import WorkspaceRole, TaskStatus
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse, WorkspaceDetail,
    ProjectCreate, ProjectUpdate, ProjectResponse,
    TaskCreate, TaskUpdate, TaskResponse,
    PaginatedResponse, InviteMember, WorkspaceMemberResponse,
)
from app.services import workspace as svc
from app.services.user import get_user_by_email

router = APIRouter()


def _ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else request.client.host


# ── Workspaces ────────────────────────────────────────────────────────────────

@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(data: WorkspaceCreate, request: Request,
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    return svc.create_workspace(db, data, current_user, _ip(request))


@router.get("", response_model=PaginatedResponse)
def list_workspaces(page: int = Query(1, ge=1),
                    page_size: int = Query(20, ge=1, le=100),
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    items, total = svc.list_user_workspaces(db, current_user.id, page, page_size)
    return PaginatedResponse(
        items=[WorkspaceResponse.model_validate(w) for w in items],
        total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 1,
    )


@router.get("/{slug}", response_model=WorkspaceDetail)
def get_workspace(slug: str, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    return svc.get_workspace_by_slug(db, slug, current_user)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(workspace_id: UUID, data: WorkspaceUpdate, request: Request,
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    return svc.update_workspace(db, workspace_id, data, current_user, _ip(request))


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(workspace_id: UUID, request: Request,
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    svc.delete_workspace(db, workspace_id, current_user, _ip(request))


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse,
             status_code=status.HTTP_201_CREATED)
def invite_member(workspace_id: UUID, payload: InviteMember, request: Request,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    from fastapi import HTTPException
    target = get_user_by_email(db, payload.email)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return svc.add_member(db, workspace_id, target, payload.role,
                          current_user, _ip(request))


# ── Projects ──────────────────────────────────────────────────────────────────

@router.post("/{workspace_id}/projects", response_model=ProjectResponse,
             status_code=status.HTTP_201_CREATED)
def create_project(workspace_id: UUID, data: ProjectCreate, request: Request,
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    return svc.create_project(db, workspace_id, data, current_user, _ip(request))


@router.get("/{workspace_id}/projects", response_model=PaginatedResponse)
def list_projects(workspace_id: UUID,
                  include_archived: bool = Query(False),
                  page: int = Query(1, ge=1),
                  page_size: int = Query(20, ge=1, le=100),
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    items, total = svc.list_projects(db, workspace_id, current_user,
                                     include_archived, page, page_size)
    return PaginatedResponse(
        items=[ProjectResponse.model_validate(p) for p in items],
        total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 1,
    )


@router.get("/{workspace_id}/projects/{project_id}", response_model=ProjectResponse)
def get_project(workspace_id: UUID, project_id: UUID,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    return svc.get_project(db, workspace_id, project_id, current_user)


@router.patch("/{workspace_id}/projects/{project_id}", response_model=ProjectResponse)
def update_project(workspace_id: UUID, project_id: UUID, data: ProjectUpdate,
                   request: Request, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    return svc.update_project(db, workspace_id, project_id, data,
                              current_user, _ip(request))


@router.delete("/{workspace_id}/projects/{project_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def delete_project(workspace_id: UUID, project_id: UUID, request: Request,
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    svc.delete_project(db, workspace_id, project_id, current_user, _ip(request))


# ── Tasks ─────────────────────────────────────────────────────────────────────

@router.post("/{workspace_id}/projects/{project_id}/tasks",
             response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(workspace_id: UUID, project_id: UUID, data: TaskCreate,
                request: Request, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    return svc.create_task(db, workspace_id, project_id, data,
                           current_user, _ip(request))


@router.get("/{workspace_id}/projects/{project_id}/tasks",
            response_model=PaginatedResponse)
def list_tasks(workspace_id: UUID, project_id: UUID,
               status_filter: Optional[str] = Query(None, alias="status"),
               assignee_id: Optional[UUID] = Query(None),
               page: int = Query(1, ge=1),
               page_size: int = Query(50, ge=1, le=200),
               db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    parsed_status = TaskStatus(status_filter) if status_filter else None
    items, total = svc.list_tasks(db, workspace_id, project_id, current_user,
                                  parsed_status, assignee_id, page, page_size)
    return PaginatedResponse(
        items=[TaskResponse.model_validate(t) for t in items],
        total=total, page=page, page_size=page_size,
        pages=math.ceil(total / page_size) if total else 1,
    )


@router.get("/{workspace_id}/projects/{project_id}/tasks/{task_id}",
            response_model=TaskResponse)
def get_task(workspace_id: UUID, project_id: UUID, task_id: UUID,
             db: Session = Depends(get_db),
             current_user: User = Depends(get_current_user)):
    return svc.get_task(db, workspace_id, project_id, task_id, current_user)


@router.patch("/{workspace_id}/projects/{project_id}/tasks/{task_id}",
              response_model=TaskResponse)
def update_task(workspace_id: UUID, project_id: UUID, task_id: UUID,
                data: TaskUpdate, request: Request,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    return svc.update_task(db, workspace_id, project_id, task_id, data,
                           current_user, _ip(request))


@router.delete("/{workspace_id}/projects/{project_id}/tasks/{task_id}",
               status_code=status.HTTP_204_NO_CONTENT)
def delete_task(workspace_id: UUID, project_id: UUID, task_id: UUID,
                request: Request, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    svc.delete_task(db, workspace_id, project_id, task_id,
                    current_user, _ip(request))