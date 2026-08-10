"""HTTP client thin a mineru-api: file_parse, tasks, health."""

import httpx

from .config import DEFAULT_TIMEOUT, MINERU_URL, PARSE_TIMEOUT


def _client(timeout: float = DEFAULT_TIMEOUT) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=MINERU_URL, timeout=timeout)


async def file_parse(path, form: dict, timeout: float = PARSE_TIMEOUT) -> dict:
    """Envía un archivo a /file_parse (síncrono)."""
    async with _client(timeout=timeout) as c:
        with open(path, "rb") as f:
            r = await c.post("/file_parse", files={"files": (path.name, f, _mime(path))}, data=form)
        r.raise_for_status()
        return r.json()


async def submit_task(path, form: dict) -> dict:
    """Envía un archivo a /tasks (asíncrono)."""
    async with _client(timeout=30.0) as c:
        with open(path, "rb") as f:
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
