from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Aline AI Doc Hub",
    description="An AI-powered document processing system for business documents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware with more secure defaults
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Should be configured more restrictively in production
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    # Expose headers for debugging
    expose_headers=["Access-Control-Allow-Origin"]
)

# Include API routers
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
def startup_event() -> None:
    """Initialize the application on startup."""
    logger.info("Starting Aline AI Doc Hub application...")
    try:
        seed.seed()
        logger.info("Database seeded successfully")
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise


@app.on_event("shutdown")
def shutdown_event() -> None:
    """Clean up resources on shutdown."""
    logger.info("Shutting down Aline AI Doc Hub application...")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log incoming requests."""
    logger.debug(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "aline-ai-doc-hub"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
