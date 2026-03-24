"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import digest, health, news


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Scheduler start/stop wired here (task 7.5)
    from app.pipeline.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="X AI News Researcher", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(news.router)
app.include_router(digest.router)
