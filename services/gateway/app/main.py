"""CanvasML Studio — API Gateway.

The central entry point for all platform services.
Handles authentication, CORS, health checks, and routes to service modules.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.gateway.app.auth import CurrentUser, Role, create_access_token, get_current_user, require_roles
from services.gateway.app.config import settings

# Import service routers
from services.connectors.catalog_api import router as catalog_router
from services.agentic.workflow_api import router as agentic_router
from services.rag.rag_api import router as rag_router
from services.observability.observability_api import router as obs_router
from services.security.security_api import router as security_router
from services.ml.ml_api import router as ml_router
from services.security.audit import AuditLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown events."""
    # Startup: verify database connectivity, warm caches, etc.
    print(f"[*] CanvasML Studio Gateway starting on port {settings.gateway_port}")
    print(f"   Environment: {settings.environment}")
    yield
    # Shutdown: clean up resources
    print("[*] Gateway shutting down")


app = FastAPI(
    title="CanvasML Studio API",
    description="AI-powered data, ML, and agentic decisioning platform for BFSI",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS & Middleware ───────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditLoggingMiddleware)

# ── Mount Service Routers ─────────────────────────────────
app.include_router(catalog_router)
app.include_router(agentic_router)
app.include_router(rag_router)
app.include_router(obs_router)
app.include_router(security_router)
app.include_router(ml_router)


# ── Health & Info ─────────────────────────────────────────


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "service": "canvasml-gateway",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/info", tags=["system"])
async def platform_info() -> dict:
    """Platform information and available modules."""
    return {
        "platform": "CanvasML Studio",
        "version": "0.1.0",
        "modules": [
            {"name": "Data Platform", "status": "planned", "phase": 1},
            {"name": "ML Platform", "status": "planned", "phase": 2},
            {"name": "XAI & Fairness", "status": "planned", "phase": 3},
            {"name": "Agentic Credit Decisioning", "status": "planned", "phase": 4},
            {"name": "Multimodal RAG", "status": "planned", "phase": 5},
            {"name": "Observability & Drift", "status": "planned", "phase": 6},
            {"name": "Console UI", "status": "planned", "phase": 7},
            {"name": "Security & Compliance", "status": "planned", "phase": 8},
        ],
    }


# ── Auth Endpoints (dev/testing) ──────────────────────────


@app.post("/auth/dev-token", tags=["auth"])
async def create_dev_token(email: str = "admin@canvasml.dev", role: str = "PlatformAdmin") -> dict:
    """Generate a development JWT token. NOT for production use.

    Available roles: PlatformAdmin, DataEngineer, DataScientist,
    RiskOfficer, BusinessUser, Auditor
    """
    if settings.environment != "development":
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev tokens disabled in non-dev environments")

    token = create_access_token(user_id="dev-user-001", email=email, role=role)
    return {"access_token": token, "token_type": "bearer", "role": role}


# ── Protected Example Endpoints ───────────────────────────


@app.get("/me", tags=["auth"])
async def get_current_user_info(user: CurrentUser = Depends(get_current_user)) -> dict:
    """Return the authenticated user's profile."""
    return {"user_id": user.user_id, "email": user.email, "role": user.role.value}


@app.get(
    "/admin/roles",
    tags=["admin"],
    dependencies=[Depends(require_roles(Role.PLATFORM_ADMIN))],
)
async def list_roles() -> dict:
    """List all platform roles. Admin only."""
    return {
        "roles": [
            {"name": r.value, "description": f"{r.value} role"}
            for r in Role
        ]
    }
