"""Configuración central: env vars, constantes y validaciones."""

import os

MINERU_URL = os.getenv("MINERU_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_BACKEND = os.getenv("MINERU_BACKEND", "pipeline")
DEFAULT_PARSE_METHOD = os.getenv("MINERU_PARSE_METHOD", "auto")
DEFAULT_LANG = os.getenv("MINERU_LANG", "es")

_LOCAL_PREFIXES = ("http://localhost", "http://127.0.0.1", "http://0.0.0.0", "http://host.docker.internal")
MINERU_IS_EXTERNAL = not any(MINERU_URL.startswith(p) for p in _LOCAL_PREFIXES)

PARSE_TIMEOUT = 300.0
DEFAULT_TIMEOUT = 15.0

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg"}

# Backends que usan VRAM — coordinan con el GPU Broker antes de parsear.
# "pipeline" también toca VRAM (modelos de layout/OCR), aunque menos que
# hybrid/vlm — bug detectado 2026-08-11/12: CUDA OOM en pipeline con
# llama-server activo porque antes no pedía nada al broker.
GPU_BACKENDS = {"pipeline", "hybrid-engine", "vlm-engine"}
GPU_BROKER = os.path.expanduser("~/stack/gpu-broker/gpu-broker.sh")
GPU_NEED_VRAM = "4000"  # MiB que MinerU necesita aprox para hybrid/vlm
GPU_VRAM_BY_BACKEND = {"pipeline": "1500", "hybrid-engine": "4000", "vlm-engine": "4000"}

SUPPORTED_LANGS = {"ch", "ch_server", "korean", "ta", "te", "ka", "th", "el", "arabic",
                   "east_slavic", "cyrillic", "devanagari"}
