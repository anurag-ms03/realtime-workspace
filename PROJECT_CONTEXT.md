# Realtime Workspace Project Context

## 1. Project Overview
Realtime Workspace is a full-stack application for managing workspaces, projects, and tasks in a collaborative environment. The project combines a FastAPI backend, a React/Vite frontend, and supporting infrastructure for PostgreSQL, Redis, and RabbitMQ.

The current implementation focuses on:
- user authentication and authorization
- workspace and project management
- task lifecycle management
- event-driven processing for notifications, auditing, and analytics
- containerized local infrastructure for development

## 2. Current Technology Stack
### Backend
- Python 3.x
- FastAPI
- SQLAlchemy
- Pydantic v2
- PostgreSQL
- Redis
- RabbitMQ via aio-pika
- Alembic for database migrations
- JWT-based authentication

### Frontend
- React
- TypeScript
- Vite
- ESLint

### Infrastructure
- Docker Compose
- PostgreSQL container
- Redis container
- RabbitMQ container

## 3. What Has Been Implemented

### 3.1 Backend Application Foundation
The backend is structured as a modular FastAPI application with:
- app startup and shutdown hooks
- CORS configuration for local frontend origins
- health endpoint for service verification
- environment-based configuration through Pydantic settings
- database session management
- API router organization for versioned endpoints

### 3.2 Authentication and User Management
Implemented authentication flows include:
- user registration
- login with email/password
- JWT access token generation
- JWT refresh token generation
- token refresh endpoint
- authenticated current-user endpoint
- password hashing and verification

The user model includes fields for:
- email
- username
- full name
- password hash
- role
- active/verified state
- timestamps

### 3.3 Workspace Domain Model
The backend includes a relational domain for:
- workspaces
- workspace members
- projects
- tasks
- audit logs

Implemented entity relationships include:
- workspace owner/admin/member roles
- workspace membership tracking
- project ownership and workspace association
- task assignment and status tracking

### 3.4 Workspace and Project APIs
The API currently supports:
- creating workspaces
- listing workspaces for the current user
- fetching a workspace by slug
- updating workspaces
- deleting workspaces
- inviting workspace members
- creating projects inside a workspace
- listing projects
- retrieving a project
- updating projects
- deleting projects

### 3.5 Task Management APIs
Task management is implemented through endpoints for:
- creating tasks under a project
- listing tasks with pagination and filtering
- retrieving a task
- updating tasks
- deleting tasks

Task features include:
- title and description
- status values such as todo, in_progress, in_review, done, cancelled
- priority levels
- assignee assignment
- due date tracking
- position tracking for ordering
- completion timestamp handling

### 3.6 Audit and Activity Tracking
The service layer records audit entries for changes such as:
- workspace creation/update/delete
- member invitation
- project creation/update/delete
- task creation/update/delete

Audit data stores:
- actor user id
- entity type and entity id
- action name
- change payload
- IP address
- timestamp

### 3.7 Event-Driven Architecture with RabbitMQ
A significant part of the project is already implemented as an asynchronous event pipeline.

Implemented event infrastructure includes:
- RabbitMQ connection manager
- topology declaration for exchanges and queues
- task event exchange and queues
- dead-letter exchange and queues
- retry delay queues for transient failures
- event publishing for task creation, update, and completion
- consumer registration and startup
- dead-letter queue inspection

Supported event types include:
- task.created
- task.updated
- task.completed

Consumers currently implemented include:
- task notification consumer
- task audit consumer
- task analytics consumer
- DLQ inspector

### 3.8 Infrastructure and Local Development Setup
The repository includes Docker Compose services for:
- PostgreSQL
- Redis
- RabbitMQ

This provides a ready-to-use local development environment for the backend services.

## 4. Project Structure

### Backend
- app/main.py: FastAPI application entrypoint
- app/api/v1/auth.py: authentication endpoints
- app/api/v1/workspaces.py: workspace, project, and task endpoints
- app/core/config.py: environment-based settings
- app/db/session.py: database session and engine configuration
- app/models/: SQLAlchemy models for users and workspace-related entities
- app/schemas/: request/response Pydantic schemas
- app/services/: business logic for users and workspace operations
- app/events/: RabbitMQ connection, topology, publishers, consumers, and schemas

### Frontend
- frontend/src/: React application entry and UI files
- frontend/package.json: frontend dependencies and scripts
- frontend/vite.config.ts: Vite configuration

## 5. Current Frontend Status
The frontend currently contains a Vite + React project scaffold. It has been initialized successfully and includes the standard starter structure.

However, the frontend is not yet a fully customized application for this project. In its current state:
- the app shell exists
- the default Vite starter UI is present
- backend integration has not yet been implemented in the UI layer

## 6. Current Project Status Summary
### Implemented
- backend service foundation
- authentication endpoints
- workspace/project/task CRUD APIs
- role-based workspace access logic
- database models and migrations structure
- RabbitMQ event pipeline infrastructure
- Docker-based local services
- initial frontend scaffold

### Not Yet Fully Completed / Still Pending
- polished production-ready frontend UI
- real UI integration with backend APIs
- end-to-end testing
- deployment configuration
- richer notification and analytics behavior beyond logging
- more advanced frontend state management and user experience flows

## 7. Suggested Mental Model for the Project
This repository is best understood as a backend-first realtime collaboration platform with event-driven processing. The core business logic is already implemented around workspaces, projects, and tasks, while the frontend is still in an early scaffold stage.

## 8. How to Run the Project
### Backend
Typical local backend setup includes:
- start required infrastructure services with Docker Compose
- configure environment variables for the database, Redis, RabbitMQ, and JWT secret
- run the FastAPI application with Uvicorn

### Frontend
The frontend can be started with the standard Vite workflow:
- install dependencies
- run the development server

## 9. Important Notes
- The backend already has a strong domain model and API foundation.
- The event-driven layer is a notable completed feature and is central to the project’s realtime-oriented architecture.
- The frontend remains the main area that still needs product-specific implementation.
