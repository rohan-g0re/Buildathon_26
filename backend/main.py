"""
AI Consulting Agency — FastAPI Entrypoint

See: docs/architecture/LLD_pipeline.md § 4

Starts the FastAPI server that exposes:
  POST /api/analyze    — start an analysis pipeline
  GET  /api/stream/:id — SSE stream for real-time progress
  GET  /api/results/:id — fetch completed results
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from utils.logger import setup_logging
from api.routes import router

# Configure logging BEFORE anything else
setup_logging()

app = FastAPI(
    title="AI Consulting Agency",
    description="Multi-layer agent pipeline for strategic business analysis",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
