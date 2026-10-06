"""Tool mineru_health: verifica que MinerU esté disponible."""

from .. import mineru_client
from ..config import MINERU_IS_EXTERNAL, MINERU_SERVICE, MINERU_URL


async def mineru_health() -> str:
    try:
        data = await mineru_client.health()
    except Exception as e:  # noqa: BLE001
        # El backend se apaga solo por idle para devolver VRAM. No hay que
        # confundir "dormido" con "roto": el health no arranca nada, pero sí
        # dice cuál de los dos es.
        _, estado = await mineru_client._systemctl("is-active", MINERU_SERVICE)
        if estado != "active":
            return ("MinerU no disponible (el backend está inactivo). "
                    "Usar parse_document o submit_parse_task para arrancarlo.")
        return f"Error: no se puede contactar MinerU en {MINERU_URL}: {type(e).__name__}: {e}"

    status = data.get("status", "unknown")
    queue = data.get("queue_depth") or data.get("pending_tasks", 0)
    workers = data.get("workers") or data.get("active_workers", "?")
    version = data.get("version") or data.get("mineru_version", "?")
    lines = [
        f"MinerU está {'disponible' if status in ('ok', 'healthy') else 'degradado'}.",
        f"URL: {MINERU_URL}",
    ]
    if MINERU_IS_EXTERNAL:
        lines.append("ADVERTENCIA: MINERU_URL apunta a un servidor EXTERNO.")
    lines += [f"Status: {status}", f"Versión: {version}", f"Tareas en cola: {queue}", f"Workers activos: {workers}"]
    return "\n".join(lines)
