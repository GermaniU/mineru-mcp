"""Tests de config: constantes y validaciones."""

from mineru_mcp.config import (
    GPU_BACKENDS,
    GPU_VRAM_BY_BACKEND,
    MINERU_IS_EXTERNAL,
    SUPPORTED_EXTENSIONS,
    SUPPORTED_LANGS,
)


def test_mineru_url_local():
    # En el entorno de test, MINERU_URL default es localhost → no external
    assert MINERU_IS_EXTERNAL is False


def test_gpu_backends():
    # Bug 2026-08-11/12: "pipeline" también toca VRAM (modelos de layout/OCR
    # de MinerU) — la asunción vieja de "pipeline = CPU-only" causaba CUDA
    # OOM sin coordinación con el GPU Broker. Ahora los tres backends
    # coordinan, cada uno con su propio requerimiento de VRAM.
    assert "pipeline" in GPU_BACKENDS
    assert "hybrid-engine" in GPU_BACKENDS
    assert "vlm-engine" in GPU_BACKENDS


def test_gpu_vram_by_backend():
    assert int(GPU_VRAM_BY_BACKEND["pipeline"]) < int(GPU_VRAM_BY_BACKEND["hybrid-engine"])
    assert GPU_VRAM_BY_BACKEND["hybrid-engine"] == GPU_VRAM_BY_BACKEND["vlm-engine"]


def test_supported_extensions():
    for ext in (".pdf", ".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg"):
        assert ext in SUPPORTED_EXTENSIONS


def test_supported_langs():
    # "es" no está en la lista (son idiomas específicos de OCR)
    assert "es" not in SUPPORTED_LANGS
    assert "ch" in SUPPORTED_LANGS
