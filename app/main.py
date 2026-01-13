from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pathlib import Path
from sqlalchemy import text
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.router import api_router
from app.database import init_db, async_session_factory
from app.config import get_settings, validate_settings
from app.connection_manager import connection_manager

# Prometheus instrumentator for HTTP metrics
instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/health"],
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Create dev user with password "dev" if dev mode is enabled
    settings = get_settings()
    validate_settings(settings)
    if settings.db_auto_create:
        await init_db()
    yield

    # Graceful shutdown: signal connections to close and wait for drain
    print("Shutdown initiated, signaling active connections...")
    connection_manager.shutdown_event.set()

    active_count = len(connection_manager.active_connections)
    if active_count > 0:
        print(f"Waiting for {active_count} active connection(s) to complete...")
        await connection_manager.wait_for_connections_to_drain(timeout=30.0)

    print("Shutdown complete")


app = FastAPI(
    title="LLM Chat Application",
    description="A conversational chat application powered by Claude",
    version="0.1.0",
    lifespan=lifespan,
)

# Instrument the app and expose /metrics endpoint
instrumentator.instrument(app).expose(app, include_in_schema=True)


def _html_response(path: Path) -> FileResponse:
    return FileResponse(
        path,
        media_type="text/html",
        headers={"Cache-Control": "no-store"},
    )

# CORS middleware for development
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(api_router)

# Static files - prefer frontend/dist (production), fall back to app/static (legacy)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
legacy_static = Path(__file__).parent / "static"

if frontend_dist.exists():
    static_path = frontend_dist
    # Vite builds assets to /assets/ directory
    app.mount("/assets", StaticFiles(directory=static_path / "assets"), name="assets")
else:
    static_path = legacy_static
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
async def serve_index():
    """Serve the main HTML page."""
    return _html_response(static_path / "index.html")


@app.get("/login.html")
async def serve_login():
    """Serve the login page."""
    return _html_response(static_path / "login.html")


@app.get("/register.html")
async def serve_register():
    """Serve the registration page."""
    return _html_response(static_path / "register.html")


@app.get("/admin")
async def serve_admin():
    """Serve the unified admin dashboard."""
    return _html_response(static_path / "admin.html")


@app.get("/admin/invites")
async def redirect_admin_invites():
    """Redirect legacy invite URL to unified admin dashboard."""
    return RedirectResponse(url="/admin", status_code=301)


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers."""
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
