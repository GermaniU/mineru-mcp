"""Tool parse_document: parseo síncrono de un documento a Markdown."""

import httpx

from .. import gpu_arbiter, mineru_client
from ..config import MINERU_IS_EXTERNAL, MINERU_URL
from ..helpers import build_form, extract_md, format_md_response, resolve_input_file


async def parse_document(
    file_path: str | None = None,
    file_base64: str | None = None,
    file_name: str | None = None,
    backend: str = "pipeline",
    effort: str = "medium",
    image_analysis: bool = False,
    parse_method: str = "auto",
    lang: str = "es",
    formula_enable: bool = True,
    table_enable: bool = True,
    start_page: int | None = None,
    end_page: int | None = None,
) -> str:
    try:
        path, is_temp = resolve_input_file(file_path, file_base64, file_name)
    except ValueError as e:
        return f"Error: {e}"

    if MINERU_IS_EXTERNAL:
        return (f"BLOQUEADO por seguridad: MINERU_URL apunta a {MINERU_URL} (servidor externo). "
                "Configurar MINERU_URL a localhost:8000 o una URL interna.")

    gpu_err = gpu_arbiter.ensure_gpu_for_mineru(backend)
    if gpu_err:
        return f"Error liberando GPU: {gpu_err}"

    try:
        form = build_form(backend, parse_method, effort, lang, formula_enable, table_enable, image_analysis)
        if start_page is not None:
            form["start_page_id"] = str(int(start_page))
        if end_page is not None:
            form["end_page_id"] = str(int(end_page))
        data = await mineru_client.file_parse(path, form)
    except httpx.ConnectError:
        return f"Error: no se puede conectar a MinerU en {MINERU_URL}."
    except httpx.TimeoutException:
        return "Error: timeout. El documento puede ser muy grande — usar submit_parse_task."
    except httpx.HTTPStatusError as e:
        return f"Error HTTP {e.response.status_code}: {e.response.text[:300]}"
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    finally:
        if is_temp:
            path.unlink(missing_ok=True)
        gpu_arbiter.release_gpu_after_mineru()

    md = extract_md(data, path.name)
    if not md.strip():
        return f"MinerU no extrajo contenido de {path.name}. El archivo puede estar vacío o protegido."
    meta = {"pages": data.get("pages") or data.get("total_pages"), "backend": form["backend"]}
    return format_md_response(md, file_name or path.name, meta)
