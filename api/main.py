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

# IDENTITY
from api.routers.identity.auth import router as auth_router
from api.routers.identity.api_keys import router as api_keys_router
from api.routers.identity.account import router as account_router
from api.routers.identity.admin import router as admin_router
from api.routers.identity.oauth_google import router as oauth_google_router
from api.routers.identity.oauth_shopify import router as oauth_shopify_router

# PROJECTS
from api.routers.projects.projects import router as projects_router

# SEO
from api.routers.seo.keywords import router as keywords_router
from api.routers.seo.speed import router as speed_router
from api.routers.seo.strategy import router as strategy_router

# CONTENT
from api.routers.content.improve import router as improve_router
from api.routers.content.article import router as article_router
from api.routers.content.feedback import router as feedback_router
from api.routers.content.shopify_improve import router as shopify_improve_router

# CMS
from api.routers.cms.integrations import router as integrations_router
from api.routers.cms.sitemap import router as sitemap_router

# AUTOMATION
from api.routers.automation.cron import router as cron_router

# INTELLIGENCE
from api.routers.intelligence.knowledge import router as knowledge_router

# OBSERVABILITY
from api.routers.observability.observability import router as observability_router

# UTILITY (no domain move)
from api.routers import skills

from core.db.base import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()  # idempotent — creates tables that don't exist yet
    from scheduler.cron import start_scheduler, stop_scheduler
    start_scheduler()
    logger.info("SEO OS API starting")
    yield
    stop_scheduler()
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
app.include_router(account_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(oauth_google_router, prefix="/api")
app.include_router(oauth_shopify_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(keywords_router, prefix="/api")
app.include_router(speed_router, prefix="/api")
app.include_router(strategy_router, prefix="/api")
app.include_router(improve_router, prefix="/api")
app.include_router(article_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(shopify_improve_router, prefix="/api")
app.include_router(integrations_router, prefix="/api")
app.include_router(sitemap_router, prefix="/api")
app.include_router(cron_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(observability_router, prefix="/api")


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health():
    return HealthResponse(status="ok", service="seo-os")


# Serve React SPA — must be last so API routes take priority
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        return FileResponse(FRONTEND_DIST / "index.html")
