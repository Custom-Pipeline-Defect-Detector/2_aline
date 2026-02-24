You are modifying an existing Dockerized full-stack app. Make changes that work fully offline with docker-compose. Do NOT add any paid/external APIs or SaaS services.

Allowed runtime services: Postgres, Redis, FastAPI, Celery worker, local filesystem storage, optional local Ollama (already present).
Disallowed: SendGrid, Twilio, Stripe, Firebase/Supabase, Google APIs, any hosted services.

====================================================
PROJECT FILES (EXACT PATHS THAT EXIST IN WORKSPACE)
====================================================

BACKEND (FastAPI / Postgres / Redis / Celery):
- /mnt/data/main.py
- /mnt/data/database.py
- /mnt/data/models.py
- /mnt/data/schemas.py
- /mnt/data/deps.py
- /mnt/data/config.py
- /mnt/data/auth.py
- /mnt/data/tasks.py
- /mnt/data/celery_app.py
- /mnt/data/seed.py
Existing routers:
- /mnt/data/dashboard.py
- /mnt/data/projects.py
- /mnt/data/proposals.py
- /mnt/data/documents.py
Optional local AI/extraction helpers (do not break):
- /mnt/data/extraction.py
- /mnt/data/mapper.py
- /mnt/data/ollama.py
- /mnt/data/prompts.py
Docker:
- /mnt/data/docker-compose.yml

FRONTEND (Vite + React + TS + Tailwind):
- /mnt/data/main.tsx
- /mnt/data/App.tsx
- /mnt/data/api.ts
- /mnt/data/styles.css
Pages:
- /mnt/data/LoginPage.tsx
- /mnt/data/RegisterPage.tsx
- /mnt/data/DashboardPage.tsx
- /mnt/data/ProjectsPage.tsx
- /mnt/data/ProjectDetailPage.tsx
- /mnt/data/ProposalsPage.tsx
- /mnt/data/ProposalDetailPage.tsx
- /mnt/data/DocumentsPage.tsx

If you need to add new files, create them in /mnt/data/ with the exact names below:
- /mnt/data/CustomersPage.tsx
- /mnt/data/CustomerDetailPage.tsx
Backend new modules (create if needed):
- /mnt/data/customers.py
- /mnt/data/notifications.py  (optional; can also be merged into dashboard.py)
- /mnt/data/doc_agent.py
- /mnt/data/agent_tools.py

Do NOT change the overall framework; follow the existing patterns in these files.

====================================================
GOALS (COMPLETE COMPANY APP)
====================================================

Build a complete internal company app (automation/engineering company) with:
1) Customers module (NO call/meeting tracking).
2) Separate dashboards per role (admin / sales / engineering / quality).
3) In-app notifications (no email/SMS).
4) Lightweight work tracking improvements (tasks, milestones, project health).
5) Agentic Ollama document automation:
   - whenever any document is uploaded, it is automatically processed in the background
   - local extraction is performed
   - gpt-oss:20b (tool-capable) classifies document type + extracts fields
   - the model uses tools to update the database (link docs, update customers/projects/proposals/tasks/notifications)
   - fully local/offline, docker-only

====================================================
NON-NEGOTIABLE CONSTRAINTS
====================================================
- No paid APIs. No external hosted services.
- Must work offline with docker-compose.
- Use Celery for background processing.
- Ollama integration must remain local-only (call the existing /mnt/data/ollama.py).
- Tool calls must be allowlisted and validated; no arbitrary execution.

====================================================
BACKEND REQUIREMENTS
====================================================

A) DATABASE MODELS (edit /mnt/data/models.py)

1) Expand Customer model (exists but minimal):
   - status: lead | active | on_hold | inactive (default lead)
   - industry: nullable string
   - notes: nullable text
   - tags: JSON array default []
   - keep existing name, aliases
   - add created_at/updated_at if not present

2) Add CustomerContact model:
   - id pk
   - customer_id fk -> customers.id (cascade delete)
   - name required
   - email nullable
   - role_title nullable
   - phone nullable
   - created_at timestamp

3) Add Notification model (in-app notifications):
   - id pk
   - user_id fk -> users.id (nullable allowed if using role notifications)
   - role nullable string (e.g., "sales", "admin") to notify all users of a role
   - type string (e.g. "task_overdue", "proposal_pending", "doc_uploaded", "needs_review")
   - message text
   - entity_table nullable string (e.g. "projects", "customers", "documents")
   - entity_id nullable int
   - is_read bool default false
   - created_at timestamp

4) Upgrade Task model (if it exists already):
   - status: open | in_progress | blocked | done (default open)
   - priority: low | med | high (default med)
   - type: engineering | manufacturing | doc | admin (default engineering)
   - completed_at nullable timestamp

5) Add Milestone model:
   - id pk
   - project_id fk -> projects.id (cascade delete)
   - name required
   - due_date nullable date
   - status planned | in_progress | done (default planned)
   - created_at timestamp

6) Add AuditEvent model if missing:
   - id pk
   - actor_user_id fk -> users.id nullable (system events allowed)
   - entity_table string
   - entity_id int
   - action string ("created","updated","deleted","status_changed","linked","classified","agent_action")
   - payload_json JSON
   - created_at timestamp

7) Document automation fields (extend Document model):
   Add:
   - processing_status: queued | processing | done | failed (default queued on upload)
   - document_type: string nullable (taxonomy below)
   - classification_confidence: float nullable
   - extracted_text: text nullable
   - extracted_fields: JSON nullable
   - agent_summary: text nullable
   - needs_review: bool default false
   - last_processed_at: datetime nullable
   - processing_error: text nullable
   Optional direct link shortcuts (if you don’t already have join tables):
   - customer_id nullable FK
   - project_id nullable FK
   (If you already have document links via join table, keep that but still add these shortcut nullable FKs if helpful.)

8) Add AgentRun model/table:
   - id pk
   - document_id fk -> documents.id
   - model string (default "gpt-oss:20b")
   - prompt_version string
   - started_at datetime
   - ended_at datetime nullable
   - tool_calls_json JSON nullable
   - final_result_json JSON nullable
   - error text nullable

B) SCHEMAS (edit /mnt/data/schemas.py)
Add Pydantic schemas:
- CustomerCreate, CustomerUpdate, CustomerOut (include contacts and summary counts)
- CustomerContactCreate, CustomerContactOut
- NotificationOut
- MilestoneCreate, MilestoneUpdate, MilestoneOut
- Document processing fields on DocumentOut (status/type/confidence/needs_review/agent_summary/extracted_fields)
- Dashboard response schemas (admin/sales/engineering/quality)
- AgentRunOut (optional)

C) ROUTERS / ENDPOINTS (keep existing style)

1) Customers router: create /mnt/data/customers.py
JWT protected:
- GET /customers?status=&q=
  Return: list with counts (active_projects, proposals_count, documents_count) and last_activity_at derived from audit/doc.
- POST /customers
- GET /customers/{id} detail:
  Include contacts + counts + linked projects list minimal (id/name/health/status)
- PATCH /customers/{id}
- DELETE /customers/{id} optional

Contacts:
- POST /customers/{id}/contacts
- DELETE /customers/{id}/contacts/{contact_id}

2) Notifications endpoints:
Prefer create /mnt/data/notifications.py (or put inside dashboard.py)
JWT protected:
- GET /notifications?unread_only=true|false
- POST /notifications/{id}/read
- POST /notifications/read_all

If notification has role set (role="sales"), GET must return notifications matching user_id OR user roles.

3) Milestones endpoints:
Add into /mnt/data/projects.py:
- POST /projects/{project_id}/milestones
- GET /projects/{project_id}/milestones
- PATCH /milestones/{id}
- DELETE /milestones/{id}

4) Dashboards (extend /mnt/data/dashboard.py):
- GET /dashboard/admin
- GET /dashboard/sales
- GET /dashboard/engineering
- GET /dashboard/quality

RBAC:
Add helper in /mnt/data/deps.py:
- require_roles(["admin", ...])
Enforce:
- /dashboard/admin -> admin only
- /dashboard/sales -> admin or sales
- /dashboard/engineering -> admin or engineer
- /dashboard/quality -> admin or quality

Dashboard data (DB only):
Admin:
- counts: users, customers, projects, proposals, documents
- queue stats: documents.processing_status counts (queued/processing/failed)
- recent audit events (last 20)
Sales:
- customers by status counts
- proposals by status counts
- stale customers (no activity in 30 days)
Engineering:
- my tasks (if assigned_to exists; else open tasks)
- blocked tasks list
- projects due soon (14 days)
Quality:
- open “issues” counts by severity (if no model exists, add ProjectIssue model)
- projects with most severe open issues
- documents needing review count

5) Document reprocess endpoint:
Add to /mnt/data/documents.py:
- POST /documents/{id}/reprocess  -> sets processing_status=queued and enqueues Celery
- Also show document processing fields in existing document list/detail responses.

D) PROJECT HEALTH
Add computed field to project list/detail:
- red: overdue high-priority tasks OR critical issues open
- yellow: blocked tasks OR milestone due within 7 days
- green: otherwise
Return in project API responses for UI badges.

E) MIGRATIONS
The system runs `alembic upgrade head` on startup (per docker-compose).
Create Alembic migration(s) for:
- customer fields
- customer_contacts
- notifications
- milestones
- audit_events
- document automation fields
- agent_runs
- task new fields (if needed)
Ensure upgrade/downgrade works.

F) SEED DATA (edit /mnt/data/seed.py)
Seed:
- at least 5 customers, each with 1-3 contacts
- at least 2 projects linked to customers
- tasks + milestones
- a few notifications (including role-based)
- a few documents in various statuses if easy
So dashboards look populated.

====================================================
AGENTIC OLLAMA DOCUMENT AUTOMATION (CORE FEATURE)
====================================================

We use local Ollama and gpt-oss:20b. The model can call tools.

Document taxonomy (fixed set):
- contract
- nda
- invoice
- purchase_order
- proposal
- sow_statement_of_work
- drawing
- spec
- report
- email_like
- other

Behavior:
- When any document is uploaded:
  1) extract text locally via extraction.py
  2) run an agent loop with gpt-oss:20b
  3) agent classifies doc_type, extracts fields into JSON, and decides which DB updates to make
  4) agent may call allowlisted tools only
  5) apply safe automation:
     - always safe: set classification, link doc, create audit event, create notifications
     - conditional: create/update customer/project/proposal/task ONLY if confidence >= 0.75 and required fields exist
     - if confidence < 0.75 or missing fields: set needs_review=true and create a review task + notification (role="admin" or "sales" depending on doc_type)

Tool system:
Create /mnt/data/agent_tools.py implementing:
- Strict allowlist of tools with Pydantic-validated args.
- Tools must read/write DB safely and return JSON results.
Required tools:
1) get_document_context(document_id)
2) set_document_classification(document_id, document_type, confidence, extracted_fields_json, agent_summary)
3) search_customers(query)
4) upsert_customer(name, aliases, industry, status)
5) search_projects(query, customer_id optional)
6) upsert_project(customer_id, name, status, due_date optional, value optional)
7) link_document(document_id, customer_id optional, project_id optional, proposal_id optional)
8) create_task(project_id optional, title, priority, type, due_date optional, assigned_to optional)
9) create_notification(message, user_id optional, role optional, entity_table optional, entity_id optional, type optional)
10) append_audit_event(entity_table, entity_id, action, payload_json, actor_user_id optional)

Agent loop:
Create /mnt/data/doc_agent.py with:
- run_document_agent(document_id, model="gpt-oss:20b", prompt_version="v1")
- builds a system prompt that:
  - describes taxonomy
  - instructs the model to always call tools to perform actions
  - asks for a final JSON result:
    {document_type, confidence, extracted_fields, actions_taken, needs_review_reason?}
- executes a tool-calling loop:
  - max tool calls = 10
  - validate tool name and args strictly
  - record all tool calls + tool results in AgentRun.tool_calls_json
- writes:
  - documents.extracted_text, extracted_fields, classification_confidence, document_type, agent_summary
  - documents.processing_status and needs_review
  - audit events for each meaningful change
- On errors: documents.processing_status="failed", documents.processing_error set.

Celery:
Modify /mnt/data/tasks.py:
- Add Celery task process_document(document_id)
  - set status processing
  - call run_document_agent
  - set done or failed
Ensure idempotency:
- if status is processing, do not start another run unless forced
Reprocess endpoint sets queued and enqueues.

====================================================
FRONTEND REQUIREMENTS (NICE, EYE-CATCHING UI)
====================================================

You MUST integrate with the existing frontend files above and keep routing structure in /mnt/data/App.tsx. Use /mnt/data/api.ts for API calls.

A) VISUAL DESIGN UPGRADE (Tailwind-only, no new UI libraries)
Make UI look modern and “premium”:
- Use a clean “app shell” layout with:
  - left sidebar (icons + labels)
  - top header (page title + search + notifications)
  - content cards with subtle gradients and shadows
- Use consistent design tokens:
  - rounded-xl, shadow-sm/md, border-gray-200, bg-slate-50 for page background
- Add tasteful micro-interactions:
  - hover states, active nav state, subtle transitions (transition-colors/transform)
- Add “status pills” (rounded-full) for:
  - project health (green/yellow/red)
  - proposal status
  - customer status
  - document processing status
- Add empty-state illustrations using simple shapes (no external images required).

You may adjust /mnt/data/styles.css to define a few utility classes like:
- .card, .card-title, .pill, .btn-primary, .btn-secondary
But keep it Tailwind-first.

B) NAVIGATION & NOTIFICATIONS
Update /mnt/data/App.tsx and relevant pages so logged-in users see:
- Sidebar links: Dashboard, Projects, Proposals, Documents, Customers
- Top bar includes:
  - global search input (local filtering per page is OK)
  - Notifications bell with unread badge

Notifications UI:
- In DashboardPage (or a shared header component created in /mnt/data):
  - fetch unread notifications
  - dropdown panel (nice card) listing latest 8
  - click marks read

C) CUSTOMERS UI (new pages)
Create:
- /mnt/data/CustomersPage.tsx
- /mnt/data/CustomerDetailPage.tsx

Routes added in /mnt/data/App.tsx:
- /customers
- /customers/:id

CustomersPage:
- header with title + “New Customer” button
- searchable/filterable table (nice card)
- columns: Name, Status pill, Industry, Active Projects count, Last Activity
- clicking row opens detail

CustomerDetailPage:
Use a tab-like UI (buttons) with sections:
- Overview (editable status, industry, notes, tags)
- Contacts (add/remove, inline cards)
- Projects (list with health pills)
- Documents (list or counts + “needs review” indicator)
- Activity (audit events list) — optional but preferred

D) DASHBOARD UI (role-based, eye catching)
Modify /mnt/data/DashboardPage.tsx:
- Determine user roles (use existing auth pattern; if needed add GET /me endpoint)
- Render the correct dashboard view (Admin/Sales/Engineering/Quality)
- Use card widgets (KPI cards) across top:
  - total customers, active projects, pending proposals, docs needing review, etc.
- Use 2-column layout with:
  - charts-like blocks but without external chart libs (use simple bar rows or mini progress bars)
  - recent activity feed card
- Add document processing widget:
  - queued/processing/failed counts
  - “needs review” count badge

E) DOCUMENTS UI: show agent results
Modify /mnt/data/DocumentsPage.tsx:
- show processing_status pill and document_type pill
- show needs_review badge
- add “Reprocess” button (calls POST /documents/{id}/reprocess)
- add collapsible panel to show:
  - agent_summary
  - extracted_fields (pretty JSON view)
- show “Processing…” state for docs with processing_status=processing

F) MINIMUM FRONTEND QUALITY BAR
- Do not break existing auth flow.
- Handle loading/error states nicely (skeleton cards or subtle spinners).
- Ensure mobile responsiveness: sidebar collapses or stacks.

====================================================
ACCEPTANCE CRITERIA
====================================================
- docker-compose up works offline.
- alembic upgrade head succeeds.
- Customer CRUD + Contacts CRUD works end-to-end.
- Role dashboards enforce RBAC (403 unauthorized).
- In-app notifications work and show unread badge.
- Document upload automatically triggers Celery processing.
- Ollama agent classifies docs, extracts fields, and uses tools to update DB.
- Low confidence results set needs_review and create a review task + notification.
- UI looks modern, clean, consistent, and “eye-catching” using Tailwind only.
- No paid/external APIs introduced.
- Keep changes scoped; follow existing code patterns.

Finished: Implemented customer, notification, milestone, dashboard, and document automation updates across backend and frontend with offline-friendly UI upgrades.
