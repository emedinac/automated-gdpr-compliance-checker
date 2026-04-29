import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Check Ollama availability on startup. Warn but don't fail — fallback works."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                if any(OLLAMA_MODEL in m for m in models):
                    logger.info(f"✓ Ollama ready — model '{OLLAMA_MODEL}' available")
                else:
                    logger.warning(
                        f"⚠ Ollama running but model '{OLLAMA_MODEL}' not found. "
                        f"Run: ollama pull {OLLAMA_MODEL}\n"
                        f"Available: {models}"
                    )
            else:
                logger.warning("⚠ Ollama not responding. Using rule-based fallback.")
    except Exception:
        logger.warning(
            f"⚠ Cannot reach Ollama at {OLLAMA_BASE_URL}. "
            "Using rule-based fallback (lower accuracy). "
            "Install Ollama: https://ollama.ai"
        )
    yield
