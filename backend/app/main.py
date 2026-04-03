"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import digest, health, news, summary


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Scheduler start/stop wired here (task 7.5)
    from app.pipeline.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="X AI News Researcher", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(news.router)
app.include_router(digest.router)
app.include_router(summary.router)
