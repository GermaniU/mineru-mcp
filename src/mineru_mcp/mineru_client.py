"""HTTP client thin a mineru-api: file_parse, tasks, health."""

import asyncio
import subprocess
import time

import httpx

from .config import (
    DEFAULT_TIMEOUT,
    MINERU_SERVICE,
    MINERU_URL,
    PARSE_TIMEOUT,
    WAKE_POLL_S,
    WAKE_TIMEOUT_S,
)


def _client(timeout: float = DEFAULT_TIMEOUT) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=MINERU_URL, timeout=timeout)


async def _reachable() -> bool:
    try:
        async with _client(timeout=3.0) as c:
            r = await c.get("/health")
            return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False


async def ensure_running() -> str | None:
    """Arranca mineru-api.service si no responde y espera a que cargue.

    El idle-watchdog apaga el backend para devolver VRAM, así que en frío
    la primera llamada tiene que despertarlo — mismo patrón que xtts_mcp y
    comfyui_mcp. Devuelve None si quedó disponible, o el mensaje de error.
    """
    if await _reachable():
        return None
    subprocess.run(["systemctl", "start", MINERU_SERVICE], capture_output=True, text=True)
    deadline = time.time() + WAKE_TIMEOUT_S
    while time.time() < deadline:
        if await _reachable():
            return None
        await asyncio.sleep(WAKE_POLL_S)
    return f"{MINERU_SERVICE} no respondió tras {WAKE_TIMEOUT_S:.0f}s de arrancarlo."


async def file_parse(path, form: dict, timeout: float = PARSE_TIMEOUT) -> dict:
    """Envía un archivo a /file_parse (síncrono)."""
    async with _client(timeout=timeout) as c:
        with open(path, "rb") as f:  # noqa: ASYNC230
            r = await c.post("/file_parse", files={"files": (path.name, f, _mime(path))}, data=form)
        r.raise_for_status()
        return r.json()


async def submit_task(path, form: dict) -> dict:
    """Envía un archivo a /tasks (asíncrono)."""
    async with _client(timeout=30.0) as c:
        with open(path, "rb") as f:  # noqa: ASYNC230
            r = await c.post("/tasks", files={"files": (path.name, f, _mime(path))}, data=form)
        r.raise_for_status()
        return r.json()


async def task_status(task_id: str) -> dict:
    async with _client() as c:
        r = await c.get(f"/tasks/{task_id}")
        r.raise_for_status()
        return r.json()


async def task_result(task_id: str) -> dict:
    async with _client(timeout=30.0) as c:
        r = await c.get(f"/tasks/{task_id}/result")
        r.raise_for_status()
        return r.json()


async def health() -> dict:
    async with _client(timeout=10.0) as c:
        r = await c.get("/health")
        r.raise_for_status()
        return r.json()


def _mime(path) -> str:
    import mimetypes
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"
