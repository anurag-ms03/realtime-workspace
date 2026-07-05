# Project File Structure

## Repository Root
```text
realtime-workspace/
├── docker-compose.yml
├── README.md
├── PROJECT_CONTEXT.md
├── PROJECT_FILE_STRUCTURE.md
├── backend/
├── frontend/
└── infra/
```

## Backend
```text
backend/
├── alembic.ini
├── requirements.txt
├── alembic/
│   ├── env.py
│   ├── README
│   └── script.py.mako
│   └── versions/
│       ├── 029c4f8fd3b7_create_users_table.py
│       └── aa70f681787a_add_workspace_project_task_audit_models.py
└── app/
    ├── __init__.py
    ├── main.py
    ├── api/
    │   ├── __init__.py
    │   ├── deps.py
    │   └── v1/
    │       ├── __init__.py
    │       ├── auth.py
    │       ├── router.py
    │       └── workspaces.py
    ├── core/
    │   ├── __init__.py
    │   ├── config.py
    │   └── security.py
    ├── db/
    │   ├── __init__.py
    │   └── session.py
    ├── events/
    │   ├── __init__.py
    │   ├── connection.py
    │   ├── consumer_runner.py
    │   ├── exchanges.py
    │   ├── idempotency.py
    │   ├── publisher.py
    │   ├── schemas.py
    │   ├── setup.py
    │   └── consumers/
    │       ├── __init__.py
    │       ├── base.py
    │       ├── dlq_inspector.py
    │       ├── task_analytics.py
    │       ├── task_audit.py
    │       └── task_notifications.py
    ├── models/
    │   ├── __init__.py
    │   ├── user.py
    │   └── workspace.py
    ├── schemas/
    │   ├── __init__.py
    │   ├── user.py
    │   └── workspace.py
    ├── services/
    │   ├── __init__.py
    │   ├── user.py
    │   └── workspace.py
    └── workers/
```

## Frontend
```text
frontend/
├── eslint.config.js
├── index.html
├── package.json
├── README.md
├── tsconfig.app.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── public/
└── src/
    ├── App.css
    ├── App.tsx
    ├── index.css
    ├── main.tsx
    └── assets/
```

## Infrastructure
```text
infra/
├── docker/
├── k8s/
└── nginx/
```

## Notes
- The backend contains the core application logic, API routes, data models, services, and RabbitMQ event consumers.
- The frontend is currently a Vite + React scaffold with the initial app entry points.
- Infrastructure folders are prepared for deployment and environment-specific configuration.
