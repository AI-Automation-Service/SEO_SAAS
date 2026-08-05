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
from api.routers.keywords import router as keywords_router
from api.routers.speed import router as speed_router
from api.routers.strategy import router as strategy_router
from api.routers.sitemap import router as sitemap_router
from api.routers.knowledge import router as knowledge_router
from api.routers.improve import router as improve_router
from api.routers.article import router as article_router
from api.routers.cron import router as cron_router
from api.routers.feedback import router as feedback_router
from api.routers.shopify_improve import router as shopify_improve_router
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
app.include_router(projects.router, prefix="/api")
app.include_router(skills.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
app.include_router(keywords_router, prefix="/api")
app.include_router(speed_router, prefix="/api")
app.include_router(strategy_router, prefix="/api")
app.include_router(sitemap_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(improve_router, prefix="/api")
app.include_router(article_router, prefix="/api")
app.include_router(cron_router, prefix="/api")
app.include_router(feedback_router, prefix="/api")
app.include_router(shopify_improve_router, prefix="/api")


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health():
    return HealthResponse(status="ok", service="seo-os")


# Serve React SPA — must be last so API routes take priority
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        return FileResponse(FRONTEND_DIST / "index.html")
