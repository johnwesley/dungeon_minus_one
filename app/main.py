from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import secrets
import base64

from app.api.router import api_router
from app.database import init_db
from app.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: initialize database
    await init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="LLM Chat Application",
    description="A conversational chat application powered by Claude",
    version="0.1.0",
    lifespan=lifespan,
)

# Basic Auth Middleware
@app.middleware("http")
async def basic_auth(request: Request, call_next):
    settings = get_settings()
    
    # Skip auth for options requests (CORS preflight)
    if request.method == "OPTIONS":
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return Response(
            content="Unauthorized", 
            status_code=401, 
            headers={"WWW-Authenticate": "Basic"}
        )

    try:
        scheme, credentials = auth_header.split()
        if scheme.lower() != 'basic':
            return Response(
                content="Unauthorized", 
                status_code=401, 
                headers={"WWW-Authenticate": "Basic"}
            )
            
        decoded = base64.b64decode(credentials).decode("ascii")
        username, _, password = decoded.partition(":")
        
        # Use secrets.compare_digest to prevent timing attacks
        is_correct_username = secrets.compare_digest(username, settings.auth_username)
        is_correct_password = secrets.compare_digest(password, settings.auth_password)
        
        if not (is_correct_username and is_correct_password):
            return Response(
                content="Unauthorized", 
                status_code=401, 
                headers={"WWW-Authenticate": "Basic"}
            )
            
    except Exception:
        return Response(
            content="Unauthorized", 
            status_code=401, 
            headers={"WWW-Authenticate": "Basic"}
        )

    response = await call_next(request)
    return response

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

# Static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/")
async def serve_index():
    """Serve the main HTML page."""
    return FileResponse(static_path / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
