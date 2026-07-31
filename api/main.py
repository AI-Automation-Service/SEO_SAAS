from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

load_dotenv(override=False)  # load .env into os.environ so SecretManager can find dynamic secrets

from api.models.responses import HealthResponse
from api.routers import integrations, projects, skills


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SEO OS API starting")
    yield
    logger.info("SEO OS API stopped")


app = FastAPI(
    title="SEO OS API",
    description="Internal SEO Operating System — manage client SEO at scale.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to specific frontend origin when UI is deployed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
