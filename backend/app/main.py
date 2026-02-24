from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from app.routers import (
    auth,
    documents,
    proposals,
    dashboard,
    projects,
    customers,
    notifications,
    tasks,
    worklogs,
    ncrs,
    issues,
    bom_items,
    inspection,
    audit,
    status,
    ai_chat,
    messages,
)
from app import seed

app = FastAPI(title="Aline AI Doc Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
    ,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(documents.router)
api_router.include_router(proposals.router)
api_router.include_router(dashboard.router)
api_router.include_router(projects.router)
api_router.include_router(customers.router)
api_router.include_router(notifications.router)
api_router.include_router(tasks.router)
api_router.include_router(worklogs.router)
api_router.include_router(ncrs.router)
api_router.include_router(issues.router)
api_router.include_router(bom_items.router)
api_router.include_router(inspection.router)
api_router.include_router(audit.router)
api_router.include_router(status.router)
api_router.include_router(ai_chat.router)
api_router.include_router(messages.router)
app.include_router(api_router)


@app.on_event("startup")
def seed_database() -> None:
    seed.seed()
