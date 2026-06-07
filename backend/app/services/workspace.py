from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID
import asyncio
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.events import publish_event, TaskCreatedEvent, TaskCreatedPayload

from datetime import datetime
from app.events import (
    publish_event,
    TaskUpdatedEvent, TaskUpdatedPayload,
    TaskCompletedEvent, TaskCompletedPayload,
)

from app.models.workspace import (
    Workspace, WorkspaceMember, Project, Task, AuditLog,
    WorkspaceRole, TaskStatus,
)
from app.models.user import User
from app.schemas.workspace import (
    WorkspaceCreate, WorkspaceUpdate,
    ProjectCreate, ProjectUpdate,
    TaskCreate, TaskUpdate,
)


import json

def _audit(db, user_id, entity_type, entity_id, action, changes=None, ip=None):
    log = AuditLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=str(entity_id),
        action=action,
        changes=json.dumps(changes) if changes else None,
        ip_address=ip,
    )
    db.add(log)


def get_member_or_403(db: Session, workspace_id: UUID, user_id: UUID) -> WorkspaceMember:
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You are not a member of this workspace")
    return member


def require_role(member: WorkspaceMember, *roles: WorkspaceRole) -> None:
    if member.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Required role: {[r.value for r in roles]}")


# ── Workspace ─────────────────────────────────────────────────────────────────

def create_workspace(db: Session, data: WorkspaceCreate,
                     current_user: User, ip=None) -> Workspace:
    if db.query(Workspace).filter(Workspace.slug == data.slug).first():
        raise HTTPException(status_code=409,
                            detail="A workspace with this slug already exists")
    workspace = Workspace(name=data.name, slug=data.slug,
                          description=data.description)
    db.add(workspace)
    db.flush()
    db.add(WorkspaceMember(workspace_id=workspace.id,
                           user_id=current_user.id,
                           role=WorkspaceRole.owner))
    _audit(db, current_user.id, "workspace", workspace.id, "created",
           {"name": data.name, "slug": data.slug}, ip)
    db.commit()
    db.refresh(workspace)
    return workspace


def list_user_workspaces(db: Session, user_id: UUID,
                         page: int = 1, page_size: int = 20) -> Tuple[List, int]:
    query = (db.query(Workspace)
               .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
               .filter(WorkspaceMember.user_id == user_id, Workspace.is_active == True))
    total = query.count()
    items = query.order_by(Workspace.created_at.desc()) \
                 .offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_workspace_by_slug(db: Session, slug: str, current_user: User) -> Workspace:
    workspace = db.query(Workspace).filter(
        Workspace.slug == slug, Workspace.is_active == True).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    get_member_or_403(db, workspace.id, current_user.id)
    return workspace


def update_workspace(db: Session, workspace_id: UUID, data: WorkspaceUpdate,
                     current_user: User, ip=None) -> Workspace:
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    member = get_member_or_403(db, workspace_id, current_user.id)
    require_role(member, WorkspaceRole.owner, WorkspaceRole.admin)
    changes = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        changes[field] = {"old": getattr(workspace, field), "new": value}
        setattr(workspace, field, value)
    workspace.updated_at = datetime.utcnow()
    _audit(db, current_user.id, "workspace", workspace_id, "updated", changes, ip)
    db.commit()
    db.refresh(workspace)
    return workspace


def delete_workspace(db: Session, workspace_id: UUID,
                     current_user: User, ip=None) -> None:
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    member = get_member_or_403(db, workspace_id, current_user.id)
    require_role(member, WorkspaceRole.owner)
    workspace.is_active = False
    workspace.updated_at = datetime.utcnow()
    _audit(db, current_user.id, "workspace", workspace_id, "deleted", None, ip)
    db.commit()


def add_member(db: Session, workspace_id: UUID, target_user: User,
               role: WorkspaceRole, current_user: User, ip=None) -> WorkspaceMember:
    member = get_member_or_403(db, workspace_id, current_user.id)
    require_role(member, WorkspaceRole.owner, WorkspaceRole.admin)
    if db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == target_user.id).first():
        raise HTTPException(status_code=409, detail="User is already a member")
    new_member = WorkspaceMember(workspace_id=workspace_id,
                                 user_id=target_user.id, role=role)
    db.add(new_member)
    _audit(db, current_user.id, "workspace_member", workspace_id, "member_added",
           {"user_id": str(target_user.id), "role": role.value}, ip)
    db.commit()
    db.refresh(new_member)
    return new_member


# ── Project ───────────────────────────────────────────────────────────────────

def create_project(db: Session, workspace_id: UUID, data: ProjectCreate,
                   current_user: User, ip=None) -> Project:
    get_member_or_403(db, workspace_id, current_user.id)
    project = Project(workspace_id=workspace_id, name=data.name,
                      description=data.description, created_by=current_user.id)
    db.add(project)
    db.flush()
    _audit(db, current_user.id, "project", project.id, "created",
           {"name": data.name}, ip)
    db.commit()
    db.refresh(project)
    return project


def list_projects(db: Session, workspace_id: UUID, current_user: User,
                  include_archived: bool = False,
                  page: int = 1, page_size: int = 20) -> Tuple[List, int]:
    get_member_or_403(db, workspace_id, current_user.id)
    query = db.query(Project).filter(Project.workspace_id == workspace_id)
    if not include_archived:
        query = query.filter(Project.is_archived == False)
    total = query.count()
    items = query.order_by(Project.created_at.desc()) \
                 .offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_project(db: Session, workspace_id: UUID, project_id: UUID,
                current_user: User) -> Project:
    get_member_or_403(db, workspace_id, current_user.id)
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.workspace_id == workspace_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def update_project(db: Session, workspace_id: UUID, project_id: UUID,
                   data: ProjectUpdate, current_user: User, ip=None) -> Project:
    project = get_project(db, workspace_id, project_id, current_user)
    member = get_member_or_403(db, workspace_id, current_user.id)
    require_role(member, WorkspaceRole.owner, WorkspaceRole.admin)
    changes = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        changes[field] = {"old": getattr(project, field), "new": value}
        setattr(project, field, value)
    project.updated_at = datetime.utcnow()
    _audit(db, current_user.id, "project", project_id, "updated", changes, ip)
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, workspace_id: UUID, project_id: UUID,
                   current_user: User, ip=None) -> None:
    project = get_project(db, workspace_id, project_id, current_user)
    member = get_member_or_403(db, workspace_id, current_user.id)
    require_role(member, WorkspaceRole.owner, WorkspaceRole.admin)
    db.delete(project)
    _audit(db, current_user.id, "project", project_id, "deleted", None, ip)
    db.commit()


# ── Task ──────────────────────────────────────────────────────────────────────

def create_task(db: Session, workspace_id: UUID, project_id: UUID,
                data: TaskCreate, current_user: User, ip=None) -> Task:
    project = get_project(db, workspace_id, project_id, current_user)
    task = Task(project_id=project.id, title=data.title,
                description=data.description, status=data.status,
                priority=data.priority, assignee_id=data.assignee_id,
                created_by=current_user.id, position=data.position,
                due_date=data.due_date)
    db.add(task)
    db.flush()
    _audit(db, current_user.id, "task", task.id, "created",
           {"title": data.title, "project_id": str(project_id)}, ip)
    db.commit()
    db.refresh(task)

    # ── Publish event ──────────────────────────────────────────────────────
    asyncio.get_event_loop().run_until_complete(
        publish_event(TaskCreatedEvent(
            payload=TaskCreatedPayload(
                task_id=str(task.id),
                project_id=str(task.project_id),
                workspace_id=str(workspace_id),
                title=task.title,
                status=task.status.value,
                priority=task.priority.value,
                created_by=str(current_user.id),
                assignee_id=str(task.assignee_id) if task.assignee_id else None,
                due_date=task.due_date,
            )
        ))
    )

    return task
   


def list_tasks(db: Session, workspace_id: UUID, project_id: UUID,
               current_user: User, status: Optional[TaskStatus] = None,
               assignee_id: Optional[UUID] = None,
               page: int = 1, page_size: int = 50) -> Tuple[List, int]:
    get_project(db, workspace_id, project_id, current_user)
    query = db.query(Task).filter(Task.project_id == project_id)
    if status:
        query = query.filter(Task.status == status)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    total = query.count()
    items = query.order_by(Task.position.asc(), Task.created_at.asc()) \
                 .offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_task(db: Session, workspace_id: UUID, project_id: UUID,
             task_id: UUID, current_user: User) -> Task:
    get_project(db, workspace_id, project_id, current_user)
    task = db.query(Task).filter(
        Task.id == task_id, Task.project_id == project_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def update_task(db: Session, workspace_id: UUID, project_id: UUID,
                task_id: UUID, data: TaskUpdate,
                current_user: User, ip=None) -> Task:
    task = get_task(db, workspace_id, project_id, task_id, current_user)
    changes = {}
    for field, value in data.model_dump(exclude_unset=True).items():
        changes[field] = {"old": str(getattr(task, field)), "new": str(value)}
        setattr(task, field, value)

    just_completed = False
    if data.status == TaskStatus.done and task.completed_at is None:
        task.completed_at = datetime.utcnow()
        just_completed = True
    elif data.status and data.status != TaskStatus.done:
        task.completed_at = None

    task.updated_at = datetime.utcnow()
    _audit(db, current_user.id, "task", task_id, "updated", changes, ip)
    db.commit()
    db.refresh(task)

    # ── Publish TaskUpdated (always) ───────────────────────────────────────
    asyncio.get_event_loop().run_until_complete(
        publish_event(TaskUpdatedEvent(
            payload=TaskUpdatedPayload(
                task_id=str(task.id),
                project_id=str(task.project_id),
                workspace_id=str(workspace_id),
                updated_by=str(current_user.id),
                changes=changes,
            )
        ))
    )

    # ── Publish TaskCompleted (only when status just flipped to done) ──────
    if just_completed:
        asyncio.get_event_loop().run_until_complete(
            publish_event(TaskCompletedEvent(
                payload=TaskCompletedPayload(
                    task_id=str(task.id),
                    project_id=str(task.project_id),
                    workspace_id=str(workspace_id),
                    title=task.title,
                    completed_by=str(current_user.id),
                    completed_at=task.completed_at,
                    assignee_id=str(task.assignee_id) if task.assignee_id else None,
                )
            ))
        )

    return task


def delete_task(db: Session, workspace_id: UUID, project_id: UUID,
                task_id: UUID, current_user: User, ip=None) -> None:
    task = get_task(db, workspace_id, project_id, task_id, current_user)
    db.delete(task)
    _audit(db, current_user.id, "task", task_id, "deleted", None, ip)
    db.commit()