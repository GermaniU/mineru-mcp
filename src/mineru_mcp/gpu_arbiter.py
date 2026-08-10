"""GPU arbiter: asegura VRAM para backends que usan GPU (hybrid/vlm)."""

import os
import subprocess

from .config import GPU_BACKENDS, GPU_BROKER, GPU_NEED_VRAM


def ensure_gpu_for_mineru(backend: str) -> str | None:
    """Si el backend usa VRAM, invoca al GPU Broker para asegurar VRAM libre.
    El broker para llama-server gracefully si está idle (espera sesiones
    activas hasta 60s), libera VRAM, y marca el estado. Al terminar el
    parseo, release_gpu_after_mineru() re-arranca llama-server."""
    if backend not in GPU_BACKENDS:
        return None
    if not os.path.isfile(GPU_BROKER) or not os.access(GPU_BROKER, os.X_OK):
        # Broker no instalado — fallback: parar ComfyUI si está activo
        r = subprocess.run(["systemctl", "is-active", "comfyui.service"],
                           capture_output=True, text=True)
        if r.stdout.strip() == "active":
            subprocess.run(["systemctl", "stop", "comfyui.service"],
                           capture_output=True, text=True)
        return None
    r = subprocess.run([GPU_BROKER, "need", "mineru", GPU_NEED_VRAM],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return f"GPU Broker no pudo asegurar VRAM: {r.stdout.strip()} {r.stderr.strip()}"
    return None


def release_gpu_after_mineru() -> None:
    """Libera la GPU al terminar el parseo — el broker re-arranca llama-server."""
    if not os.path.isfile(GPU_BROKER) or not os.access(GPU_BROKER, os.X_OK):
        return
    subprocess.run([GPU_BROKER, "release", "mineru"],
                   capture_output=True, text=True, timeout=60)
