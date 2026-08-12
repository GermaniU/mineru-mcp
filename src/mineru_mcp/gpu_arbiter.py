"""GPU arbiter: asegura VRAM para backends que usan GPU (pipeline/hybrid/vlm).

Cada llamada a ensure_gpu_for_mineru() genera un client_id único y lo registra
como "holder" en el GPU Broker. release_gpu_after_mineru() debe llamarse con
ESE MISMO client_id cuando el trabajo real en GPU terminó — no antes. El
broker solo re-arranca llama-server cuando el último holder se libera
(reference counting), evitando la carrera detectada 2026-08-11/12: el
release disparado apenas se enviaba una tarea async (submit_parse_task)
reiniciaba llama-server mientras mineru-api todavía estaba procesando en
la GPU.
"""

import os
import subprocess
import uuid

from .config import GPU_BACKENDS, GPU_BROKER, GPU_NEED_VRAM, GPU_VRAM_BY_BACKEND


def ensure_gpu_for_mineru(backend: str) -> tuple[str | None, str | None]:
    """Si el backend usa VRAM, invoca al GPU Broker para asegurar VRAM libre.
    Devuelve (error, client_id). client_id es None si este backend no toca
    GPU (nada que liberar después). Si hay error, client_id también es None.
    """
    if backend not in GPU_BACKENDS:
        return None, None

    client_id = uuid.uuid4().hex[:12]

    if not os.path.isfile(GPU_BROKER) or not os.access(GPU_BROKER, os.X_OK):
        # Broker no instalado — fallback: parar ComfyUI si está activo
        r = subprocess.run(["systemctl", "is-active", "comfyui.service"],
                           capture_output=True, text=True, check=False)
        if r.stdout.strip() == "active":
            subprocess.run(["systemctl", "stop", "comfyui.service"],
                           capture_output=True, text=True, check=False)
        return None, None

    vram = GPU_VRAM_BY_BACKEND.get(backend, GPU_NEED_VRAM)
    r = subprocess.run([GPU_BROKER, "need", "mineru", vram, client_id],
                       capture_output=True, text=True, timeout=120, check=False)
    if r.returncode != 0:
        return f"GPU Broker no pudo asegurar VRAM: {r.stdout.strip()} {r.stderr.strip()}", None
    return None, client_id


def release_gpu_after_mineru(client_id: str | None) -> None:
    """Libera la GPU al terminar el trabajo REAL en GPU (no al enviar la
    tarea async). El broker re-arranca llama-server solo si no quedan
    otros holders activos. No-op si client_id es None (este backend nunca
    tomó GPU)."""
    if client_id is None:
        return
    if not os.path.isfile(GPU_BROKER) or not os.access(GPU_BROKER, os.X_OK):
        return
    subprocess.run([GPU_BROKER, "release", "mineru", client_id],
                   capture_output=True, text=True, timeout=60, check=False)
