import asyncio

from automatedcompliancechecker.services import model_manager as model_manager_module
from automatedcompliancechecker.services.model_manager import ModelManager, stop_model_task


def test_ensure_model_pulls_missing_model_once():
    manager = ModelManager(base_url="http://ollama:11434", model_name="gemma3:4b")
    calls = {"exists": 0, "pull": 0}

    async def model_exists() -> bool:
        calls["exists"] += 1
        manager.status.ollama_up = True
        return False

    async def pull_model() -> None:
        calls["pull"] += 1

    manager._model_exists = model_exists
    manager._pull_model = pull_model

    asyncio.run(manager.ensure_model())

    assert manager.ready is True
    assert calls == {"exists": 1, "pull": 1}


def test_ensure_model_skips_pull_when_model_exists():
    manager = ModelManager(base_url="http://ollama:11434", model_name="gemma3:4b")
    calls = {"exists": 0, "pull": 0}

    async def model_exists() -> bool:
        calls["exists"] += 1
        manager.status.ollama_up = True
        return True

    async def pull_model() -> None:
        calls["pull"] += 1

    manager._model_exists = model_exists
    manager._pull_model = pull_model

    asyncio.run(manager.ensure_model())

    assert manager.ready is True
    assert calls == {"exists": 1, "pull": 0}


def test_model_exists_reads_ollama_tags(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"models": [{"name": "gemma3:4b"}]}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            self.url = url
            return FakeResponse()

    monkeypatch.setattr(model_manager_module.httpx, "AsyncClient", FakeClient)

    manager = ModelManager(base_url="http://ollama:11434/", model_name="gemma3:4b")

    assert asyncio.run(manager._model_exists()) is True
    assert manager.status.ollama_up is True


def test_model_exists_returns_false_when_configured_model_is_missing(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"models": [{"name": "llama3:8b"}]}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            return FakeResponse()

    monkeypatch.setattr(model_manager_module.httpx, "AsyncClient", FakeClient)

    manager = ModelManager(base_url="http://ollama:11434", model_name="gemma3:4b")

    assert asyncio.run(manager._model_exists()) is False


def test_pull_model_calls_ollama_pull_endpoint(monkeypatch):
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json):
            calls["url"] = url
            calls["json"] = json
            return FakeResponse()

    monkeypatch.setattr(model_manager_module.httpx, "AsyncClient", FakeClient)

    manager = ModelManager(base_url="http://ollama:11434", model_name="gemma3:4b")

    asyncio.run(manager._pull_model())

    assert manager.status.pulling is False
    assert calls == {
        "url": "http://ollama:11434/api/pull",
        "json": {"name": "gemma3:4b", "stream": False},
    }


def test_ensure_model_records_errors_and_retries(monkeypatch):
    manager = ModelManager(base_url="http://ollama:11434", model_name="gemma3:4b")
    calls = {"exists": 0, "sleep": 0}

    async def model_exists() -> bool:
        calls["exists"] += 1
        if calls["exists"] == 1:
            raise RuntimeError("ollama unavailable")
        manager.status.ollama_up = True
        return True

    async def fake_sleep(seconds: int) -> None:
        calls["sleep"] += 1

    manager._model_exists = model_exists
    monkeypatch.setattr(model_manager_module.asyncio, "sleep", fake_sleep)

    asyncio.run(manager.ensure_model())

    assert manager.ready is True
    assert calls == {"exists": 2, "sleep": 1}


def test_stop_model_task_accepts_none():
    asyncio.run(stop_model_task(None))


def test_stop_model_task_cancels_running_task():
    async def run_test():
        cancelled = False

        async def never_finishes():
            nonlocal cancelled
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                cancelled = True
                raise

        task = asyncio.create_task(never_finishes())
        await asyncio.sleep(0)
        await stop_model_task(task)
        assert cancelled is True

    asyncio.run(run_test())
