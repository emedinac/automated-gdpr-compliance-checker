import asyncio
import contextlib
import os
from dataclasses import dataclass

import httpx
import structlog
from fastapi import HTTPException

logger = structlog.get_logger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


@dataclass
class ModelStatus:
    provider: str = LLM_PROVIDER
    ollama_up: bool = False
    model_ready: bool = False
    model_name: str = OLLAMA_MODEL
    base_url: str = OLLAMA_BASE_URL
    api_key_configured: bool = False
    last_error: str | None = None
    pulling: bool = False


class ModelManager:
    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        provider: str = LLM_PROVIDER,
        api_key: str | None = OPENAI_API_KEY,
    ):
        self.provider = provider.lower()
        if self.provider not in {"ollama", "openai"}:
            raise ValueError("LLM_PROVIDER must be either 'ollama' or 'openai'")

        default_base_url = OPENAI_BASE_URL if self.provider == "openai" else OLLAMA_BASE_URL
        default_model_name = OPENAI_MODEL if self.provider == "openai" else OLLAMA_MODEL

        self.api_key = api_key
        self.api_key_configured = bool(api_key) if self.provider == "openai" else True
        self.base_url = (base_url or default_base_url).rstrip("/")
        self.model_name = model_name or default_model_name
        self.status = ModelStatus(
            provider=self.provider,
            model_name=self.model_name,
            base_url=self.base_url,
            api_key_configured=self.api_key_configured,
        )
        self._lock = asyncio.Lock()

    @property
    def ready(self) -> bool:
        return self.status.model_ready

    async def ensure_model(self) -> None:
        """Ensure the configured model provider is ready without blocking FastAPI startup."""
        async with self._lock:
            if self.provider == "openai":
                self._mark_openai_ready()
                return

            while not self.ready:
                try:
                    if await self._model_exists():
                        self.status.model_ready = True
                        self.status.pulling = False
                        self.status.last_error = None
                        logger.info("ollama.model_ready", model=self.model_name)
                        return

                    await self._pull_model()
                    self.status.ollama_up = True
                    self.status.model_ready = True
                    self.status.last_error = None
                    logger.info("ollama.model_ready", model=self.model_name)
                    return
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self.status.ollama_up = False
                    self.status.model_ready = False
                    self.status.pulling = False
                    self.status.last_error = str(exc)
                    logger.warning("ollama.model_unavailable", model=self.model_name, error=str(exc))

                await asyncio.sleep(5)

    def _mark_openai_ready(self) -> None:
        self.status.ollama_up = True
        self.status.pulling = False
        self.status.api_key_configured = bool(self.api_key)

        if not self.api_key:
            self.status.model_ready = False
            self.status.last_error = "OPENAI_API_KEY is not configured."
            logger.warning("openai.api_key_missing", model=self.model_name)
            return

        self.status.model_ready = True
        self.status.last_error = None
        logger.info("openai.model_configured", model=self.model_name, base_url=self.base_url)

    async def _model_exists(self) -> bool:
        timeout = httpx.Timeout(10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()

        self.status.ollama_up = True
        models = response.json().get("models", [])
        names = {model.get("name") for model in models}
        return self.model_name in names

    async def _pull_model(self) -> None:
        self.status.pulling = True
        self.status.last_error = None
        logger.info("ollama.model_pull_started", model=self.model_name)

        timeout = httpx.Timeout(connect=10.0, read=None, write=10.0, pool=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model_name, "stream": False},
            )
            response.raise_for_status()

        self.status.pulling = False
        logger.info("ollama.model_pull_completed", model=self.model_name)

    def snapshot(self) -> ModelStatus:
        return ModelStatus(
            ollama_up=self.status.ollama_up,
            model_ready=self.status.model_ready,
            model_name=self.status.model_name,
            base_url=self.status.base_url,
            provider=self.status.provider,
            api_key_configured=self.status.api_key_configured,
            last_error=self.status.last_error,
            pulling=self.status.pulling,
        )


model_manager = ModelManager()


def require_model_ready() -> None:
    if model_manager.ready:
        return

    status = model_manager.snapshot()
    detail = "Model is still loading. Try again shortly."
    if status.last_error:
        detail = f"{detail} Last provider error: {status.last_error}"

    raise HTTPException(status_code=503, detail=detail)


async def stop_model_task(task: asyncio.Task | None) -> None:
    if task is None:
        return

    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
