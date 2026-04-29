import asyncio

from fastapi import FastAPI

from automatedcompliancechecker import main
from automatedcompliancechecker.utils import lifespan as lifespan_module


def test_health_endpoint_function():
    assert main.health() == {"status": "ok"}


def test_lifespan_starts_and_cancels_model_task(monkeypatch):
    async def run_lifespan():
        cancelled = False

        async def fake_ensure_model():
            nonlocal cancelled
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                cancelled = True
                raise

        monkeypatch.setattr(lifespan_module.model_manager, "ensure_model", fake_ensure_model)

        app = FastAPI()
        async with lifespan_module.lifespan(app):
            assert app.state.model_manager is lifespan_module.model_manager
            assert app.state.model_task is not None
            await asyncio.sleep(0)

        assert cancelled is True

    asyncio.run(run_lifespan())
