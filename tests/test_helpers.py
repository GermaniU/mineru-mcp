"""Tests de helpers: form, extracción de markdown, resolución de input."""

import pytest

from mineru_mcp.helpers import build_form, extract_md, format_md_response, resolve_input_file


def test_build_form_defaults():
    form = build_form("pipeline", "auto", "medium", "es", True, True, False)
    assert form["backend"] == "pipeline"
    assert form["return_md"] == "true"
    # "es" no está en SUPPORTED_LANGS → no se agrega lang_list
    assert "lang_list" not in form


def test_build_form_lang_soportado():
    # "ch" sí está en SUPPORTED_LANGS → se agrega lang_list
    form = build_form("pipeline", "auto", "medium", "ch", True, True, False)
    assert form["lang_list"] == "ch"


def test_extract_md_directo():
    assert extract_md({"md": "hola"}, "x.pdf") == "hola"
    assert extract_md({"md_content": "mundo"}, "x.pdf") == "mundo"


def test_extract_md_results_dict():
    data = {"results": {"file": {"md_content": "contenido"}}}
    assert extract_md(data, "x.pdf") == "contenido"


def test_extract_md_fallback():
    out = extract_md({}, "x.pdf")
    assert "no devolvió markdown" in out


def test_format_md_response():
    out = format_md_response("cuerpo", "doc.pdf", {"pages": 5, "backend": "pipeline"})
    assert "## Documento: doc.pdf" in out
    assert "**Páginas:** 5" in out
    assert "cuerpo" in out


def test_resolve_input_file_requiere_algo():
    with pytest.raises(ValueError):
        resolve_input_file(None, None, None)


def test_resolve_input_file_base64_sin_name():
    with pytest.raises(ValueError):
        resolve_input_file(None, "AAAA", None)


def test_resolve_input_file_extension_no_soportada():
    with pytest.raises(ValueError):
        resolve_input_file(None, "AAAA", "file.xyz")
