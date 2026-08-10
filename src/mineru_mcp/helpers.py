"""Helpers: form de parseo, extracción de markdown, resolución de input."""

import base64
import tempfile
from pathlib import Path

from .config import (DEFAULT_BACKEND, DEFAULT_LANG, DEFAULT_PARSE_METHOD,
                     SUPPORTED_EXTENSIONS, SUPPORTED_LANGS)


def build_form(backend: str, parse_method: str, effort: str, lang: str,
               formula_enable: bool, table_enable: bool, image_analysis: bool) -> dict:
    form: dict = {
        "backend": backend or DEFAULT_BACKEND,
        "parse_method": parse_method or DEFAULT_PARSE_METHOD,
        "effort": effort or "medium",
        "formula_enable": str(formula_enable).lower(),
        "table_enable": str(table_enable).lower(),
        "image_analysis": str(image_analysis).lower(),
        "return_md": "true",
        "return_content_list": "false",
        "return_middle_json": "false",
        "return_images": "false",
        "response_format_zip": "false",
    }
    lang = (lang or DEFAULT_LANG).strip()
    if lang in SUPPORTED_LANGS:
        form["lang_list"] = lang
    return form


def extract_md(data: dict, filename: str) -> str:
    if "results" in data and isinstance(data["results"], dict):
        for _name, content in data["results"].items():
            if isinstance(content, dict):
                md = content.get("md_content") or content.get("md", "")
                if md:
                    return md
    if "md" in data:
        return data["md"]
    if "md_content" in data:
        return data["md_content"]
    results = data.get("results") or []
    if isinstance(results, list) and results:
        r = results[0]
        if isinstance(r, dict):
            return r.get("md_content") or r.get("md", "")
    for key in ("markdown", "content", "text"):
        if key in data and isinstance(data[key], str) and len(data[key]) > 50:
            return data[key]
    return f"[MinerU no devolvió markdown para {filename}. Respuesta: {str(data)[:300]}]"


def format_md_response(md: str, filename: str, meta: dict | None = None) -> str:
    parts = [f"## Documento: {filename}\n"]
    if meta:
        if meta.get("pages"):
            parts.append(f"**Páginas:** {meta['pages']}")
        if meta.get("backend"):
            parts.append(f"**Backend:** {meta['backend']}")
        parts.append("")
    parts.append(md)
    return "\n".join(parts)


def resolve_input_file(file_path: str | None, file_base64: str | None,
                       file_name: str | None) -> tuple[Path, bool]:
    """Devuelve (path_local_en_popos, es_temporal). Lanza ValueError si ninguno
    de los dos modos de entrada es válido."""
    if file_base64:
        if not file_name:
            raise ValueError("file_name es obligatorio junto con file_base64.")
        suffix = Path(file_name).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Extensión '{suffix}' no soportada. Soportadas: {', '.join(SUPPORTED_EXTENSIONS)}")
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(base64.b64decode(file_base64))
        tmp.close()
        return Path(tmp.name), True
    if file_path:
        p = Path(file_path.strip())
        if not p.exists():
            raise ValueError(f"Archivo no encontrado en Pop!_OS: {p}")
        if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Extensión '{p.suffix}' no soportada. Soportadas: {', '.join(SUPPORTED_EXTENSIONS)}")
        return p, False
    raise ValueError("Se requiere file_path (ruta en Pop!_OS) o file_base64+file_name (contenido).")
