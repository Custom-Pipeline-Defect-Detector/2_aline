from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.routers import (
    auth,
    documents,
    proposals,
    dashboard,
    inbox,
    quality,
    document_processing,
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
    search,
)
from app import seed
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AutoDev Automation Platform",
    description="An automation platform for engineering companies with document processing, project management, and workflow tools",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add security-related middlewares
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add Trusted Host Middleware to prevent HTTP Host Header attacks
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # Should be configured more restrictively in production

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
api_router.include_router(inbox.router)
api_router.include_router(quality.router)
api_router.include_router(document_processing.router)
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
    logger.info("Starting AutoDev Automation Platform application...")
    # Skip seeding during startup to avoid table creation issues
    # Database should be initialized separately using init_db.py
    # try:
    #     seed.seed()
    #     logger.info("Database seeded successfully")
    # except Exception as e:
    #     logger.error(f"Error during startup: {str(e)}")
    #     raise


@app.on_event("shutdown")
def shutdown_event() -> None:
    """Clean up resources on shutdown."""
    logger.info("Shutting down AutoDev Automation Platform application...")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log incoming requests."""
    logger.debug(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "autodev-automation-platform"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Serve static files from the frontend build directory if it exists
frontend_dist_path = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist_path.exists():
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="static")
else:
    logger.warning(f"Frontend dist directory does not exist: {frontend_dist_path}")
