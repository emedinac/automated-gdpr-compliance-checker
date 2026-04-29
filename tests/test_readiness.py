import pytest
from fastapi import HTTPException

from automatedcompliancechecker.services import model_manager as model_manager_module


def test_require_model_ready_allows_requests_when_model_is_ready():
    status = model_manager_module.model_manager.status
    original = status.ollama_up, status.model_ready, status.last_error
    status.ollama_up = True
    status.model_ready = True
    status.last_error = None

    try:
        model_manager_module.require_model_ready()
    finally:
        status.ollama_up, status.model_ready, status.last_error = original


def test_require_model_ready_returns_503_when_model_is_loading():
    status = model_manager_module.model_manager.status
    original = status.ollama_up, status.model_ready, status.last_error
    status.ollama_up = True
    status.model_ready = False
    status.last_error = None

    try:
        with pytest.raises(HTTPException) as exc_info:
            model_manager_module.require_model_ready()
    finally:
        status.ollama_up, status.model_ready, status.last_error = original

    assert exc_info.value.status_code == 503
    assert "Model is still loading" in exc_info.value.detail


def test_require_model_ready_includes_last_ollama_error():
    status = model_manager_module.model_manager.status
    original = status.ollama_up, status.model_ready, status.last_error
    status.ollama_up = False
    status.model_ready = False
    status.last_error = "connection refused"

    try:
        with pytest.raises(HTTPException) as exc_info:
            model_manager_module.require_model_ready()
    finally:
        status.ollama_up, status.model_ready, status.last_error = original

    assert exc_info.value.status_code == 503
    assert "connection refused" in exc_info.value.detail

