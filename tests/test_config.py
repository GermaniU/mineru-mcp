"""Tests de config: constantes y validaciones."""

from mineru_mcp.config import (GPU_BACKENDS, MINERU_IS_EXTERNAL, MINERU_URL,
                               SUPPORTED_EXTENSIONS, SUPPORTED_LANGS)


def test_mineru_url_local():
    # En el entorno de test, MINERU_URL default es localhost → no external
    assert MINERU_IS_EXTERNAL is False


def test_gpu_backends():
    assert "hybrid-engine" in GPU_BACKENDS
    assert "vlm-engine" in GPU_BACKENDS
    assert "pipeline" not in GPU_BACKENDS


def test_supported_extensions():
    for ext in (".pdf", ".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg"):
        assert ext in SUPPORTED_EXTENSIONS


def test_supported_langs():
    # "es" no está en la lista (son idiomas específicos de OCR)
    assert "es" not in SUPPORTED_LANGS
    assert "ch" in SUPPORTED_LANGS
