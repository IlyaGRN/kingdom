"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.routes import router as api_router
from app.api.websocket import router as ws_router

settings = get_settings()

app = FastAPI(
    title="Machiavelli's Kingdom",
    description="A Medieval Strategy Board Game API",
    version="1.0.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api")
app.include_router(ws_router, prefix="/ws")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "game": "Machiavelli's Kingdom"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}



