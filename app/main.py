from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy import select, text

from app.api.router import api_router
from app.database import init_db, async_session_factory
from app.config import get_settings, validate_settings
from app.models.database import User
from app.services.auth_service import get_password_hash
from app.connection_manager import connection_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Create dev user with password "dev" if dev mode is enabled
    settings = get_settings()
    validate_settings(settings)
    if settings.db_auto_create:
        await init_db()
    if settings.dev_auth_bypass:
        async with async_session_factory() as session:
            result = await session.execute(select(User).where(User.username == "dev"))
            dev_user = result.scalar_one_or_none()
            if not dev_user:
                dev_user = User(username="dev", hashed_password=get_password_hash("dev"))
                session.add(dev_user)
                await session.commit()

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

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    return FileResponse(static_path / "index.html")


@app.get("/login.html")
async def serve_login():
    """Serve the login page."""
    return FileResponse(static_path / "login.html")


@app.get("/register.html")
async def serve_register():
    """Serve the registration page."""
    return FileResponse(static_path / "register.html")


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
