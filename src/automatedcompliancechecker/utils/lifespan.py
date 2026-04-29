import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from automatedcompliancechecker.services.model_manager import model_manager, stop_model_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_task = asyncio.create_task(model_manager.ensure_model())
    app.state.model_manager = model_manager
    app.state.model_task = model_task

    try:
        yield
    finally:
        await stop_model_task(model_task)
