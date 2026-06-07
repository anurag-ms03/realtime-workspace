"""
Exchange and queue name constants.
All event infrastructure is declared here — import from this module only.
"""

# ── Exchanges ──────────────────────────────────────────────────────────────
TASK_EVENTS_EXCHANGE = "task.events"        # topic exchange for task domain

# ── Routing keys ───────────────────────────────────────────────────────────
ROUTING_KEY_TASK_CREATED   = "task.created"
ROUTING_KEY_TASK_COMPLETED = "task.completed"
ROUTING_KEY_TASK_UPDATED   = "task.updated"

# ── Queues ─────────────────────────────────────────────────────────────────
QUEUE_TASK_NOTIFICATIONS   = "task.notifications"   # email / in-app alerts
QUEUE_TASK_AUDIT           = "task.audit"           # audit log writer
QUEUE_TASK_ANALYTICS       = "task.analytics"       # metrics / reporting

# ── Dead-letter ────────────────────────────────────────────────────────────
DLX_EXCHANGE               = "dead.letter.exchange"
DLQ_TASK_NOTIFICATIONS     = "dlq.task.notifications"
DLQ_TASK_AUDIT             = "dlq.task.audit"
DLQ_TASK_ANALYTICS         = "dlq.task.analytics"