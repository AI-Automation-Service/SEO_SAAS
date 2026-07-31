from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

load_dotenv(override=False)  # load .env before any module reads os.environ

from api.models.responses import HealthResponse
from api.routers import integrations, projects, skills
from api.routers.auth import router as auth_router
from api.routers.api_keys import router as api_keys_router
from core.db.base import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()  # idempotent — creates tables that don't exist yet
    logger.info("SEO OS API starting")
    yield
    logger.info("SEO OS API stopped")


app = FastAPI(
    title="SEO OS API",
    description="Multi-tenant SEO Operating System.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to specific origin when domain is configured
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(api_keys_router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health():
    return HealthResponse(status="ok", service="seo-os")


# Serve React SPA — must be last so API routes take priority
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        return FileResponse(FRONTEND_DIST / "index.html")
