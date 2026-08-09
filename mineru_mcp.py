#!/usr/bin/env python3
"""
MCP HTTP/SSE server que expone MinerU como herramienta de parsing de documentos.

Corre EN Pop!_OS junto con mineru-api (a diferencia del diseño original WSL/stdio):
cualquier gateway Hermes de la LAN lo consume vía HTTP en el puerto 8202, sin
instalar nada localmente — mismo patrón que vault_rw.py / comfyui_mcp.py.

MinerU convierte PDFs, DOCX, PPTX, XLSX e imágenes a Markdown + JSON estructurado.

Tools expuestas:
  parse_document         parseo síncrono: devuelve Markdown directamente (~30-120s)
  submit_parse_task      envío asíncrono: devuelve task_id para docs grandes
  get_task_status        consulta estado de una tarea asíncrona
  get_task_result        obtiene el Markdown de una tarea completada
  mineru_health          verifica que el servidor MinerU esté vivo

Backends (elegible por request, NO fijo por config — ver arg `backend`):
  pipeline       rápido, sin GPU — no compite por VRAM con el LLM/ComfyUI.
  hybrid-engine  mejor balance, usa VLM en bloques difíciles (~4GB VRAM) — SÍ
                 compite por GPU. Con effort=high + image_analysis=true da
                 diagramas Mermaid de las figuras.
  vlm-engine     máxima precisión por página (~4GB VRAM) — SÍ compite por GPU.

GPU arbiter: backends que usan VRAM (hybrid-engine/vlm-engine) llaman a
ensure_gpu_for_mineru() antes de parsear — invoca al GPU Broker
(~/stack/gpu-broker/gpu-broker.sh) que para llama-server gracefully si está
idle, espera liberación de VRAM, y re-arranca llama-server al terminar.
pipeline no toca el arbiter (no usa GPU).

Archivo a parsear — DOS formas:
  file_path     ruta en el filesystem DE POP!_OS (si el doc ya vive ahí).
  file_base64 + file_name   contenido del archivo en base64 (para callers
                remotos, ej. el gateway Hermes de la Mac/Air) — se decodifica
                a un temporal en Pop!_OS y se borra al terminar.

Configuración (vars de entorno):
  MINERU_URL             URL base del servidor mineru-api (default: http://127.0.0.1:8000)
  MINERU_BACKEND         backend default si no se especifica por request (default: pipeline)
  MINERU_PARSE_METHOD    método de extracción: auto | txt | ocr  (default: auto)
  MCP_PORT               default 8202
  MCP_HOST               default 0.0.0.0
"""
import base64
import mimetypes
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
import uvicorn

MINERU_URL = os.getenv("MINERU_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_BACKEND = os.getenv("MINERU_BACKEND", "pipeline")
DEFAULT_PARSE_METHOD = os.getenv("MINERU_PARSE_METHOD", "auto")
DEFAULT_LANG = os.getenv("MINERU_LANG", "es")

_LOCAL_PREFIXES = ("http://localhost", "http://127.0.0.1", "http://0.0.0.0", "http://host.docker.internal")
_MINERU_IS_EXTERNAL = not any(MINERU_URL.startswith(p) for p in _LOCAL_PREFIXES)

PARSE_TIMEOUT = 300.0
DEFAULT_TIMEOUT = 15.0

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg"}

# Backends que usan VRAM — coordinan con el GPU Broker antes de parsear.
_GPU_BACKENDS = {"hybrid-engine", "vlm-engine"}
GPU_BROKER = os.path.expanduser("~/stack/gpu-broker/gpu-broker.sh")
GPU_NEED_VRAM = "4000"  # MiB que MinerU necesita aprox para hybrid/vlm

_SUPPORTED_LANGS = {"ch", "ch_server", "korean", "ta", "te", "ka", "th", "el", "arabic",
                     "east_slavic", "cyrillic", "devanagari"}

mcp = FastMCP("mineru")


# ─── GPU arbiter (solo si el backend pedido usa VRAM) ────────────────────

def ensure_gpu_for_mineru(backend: str) -> str | None:
    """Si el backend usa VRAM, invoca al GPU Broker para asegurar VRAM libre.
    El broker para llama-server gracefully si está idle (espera sesiones
    activas hasta 60s), libera VRAM, y marca el estado. Al terminar el
    parseo, release_gpu_after_mineru() re-arranca llama-server."""
    if backend not in _GPU_BACKENDS:
        return None
    if not os.path.isfile(GPU_BROKER) or not os.access(GPU_BROKER, os.X_OK):
        # Broker no instalado — fallback: parar ComfyUI si está activo
        r = subprocess.run(["systemctl", "is-active", "comfyui.service"], capture_output=True, text=True)
        if r.stdout.strip() == "active":
            subprocess.run(["systemctl", "stop", "comfyui.service"], capture_output=True, text=True)
        return None
    r = subprocess.run([GPU_BROKER, "need", "mineru", GPU_NEED_VRAM], capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return f"GPU Broker no pudo asegurar VRAM: {r.stdout.strip()} {r.stderr.strip()}"
    return None


def release_gpu_after_mineru() -> None:
    """Libera la GPU al terminar el parseo — el broker re-arranca llama-server."""
    if not os.path.isfile(GPU_BROKER) or not os.access(GPU_BROKER, os.X_OK):
        return
    subprocess.run([GPU_BROKER, "release", "mineru"], capture_output=True, text=True, timeout=60)


# ─── Helpers ──────────────────────────────────────────────────────────────

def _client(timeout: float = DEFAULT_TIMEOUT) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=MINERU_URL, timeout=timeout)


def _mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _build_form(backend: str, parse_method: str, effort: str, lang: str,
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
    if lang in _SUPPORTED_LANGS:
        form["lang_list"] = lang
    return form


def _extract_md(data: dict, filename: str) -> str:
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


def _format_md_response(md: str, filename: str, meta: dict | None = None) -> str:
    parts = [f"## Documento: {filename}\n"]
    if meta:
        if meta.get("pages"):
            parts.append(f"**Páginas:** {meta['pages']}")
        if meta.get("backend"):
            parts.append(f"**Backend:** {meta['backend']}")
        parts.append("")
    parts.append(md)
    return "\n".join(parts)


def _resolve_input_file(file_path: str | None, file_base64: str | None, file_name: str | None) -> tuple[Path, bool]:
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


# ─── Tools ───────────────────────────────────────────────────────────────

@mcp.tool(
    name="parse_document",
    description=(
        "Parsea un documento (PDF, DOCX, PPTX, XLSX, imagen) con MinerU y devuelve "
        "su contenido como Markdown estructurado (texto, tablas, fórmulas, títulos). "
        "Enviar el archivo con file_path (si ya vive en Pop!_OS) o file_base64+file_name "
        "(contenido, para callers remotos). backend=pipeline es rápido y sin GPU; "
        "hybrid-engine/vlm-engine usan ~4GB VRAM (GPU Broker para llama-server "
        "automáticamente, lo re-arranca al terminar) y dan mejor calidad — "
        "hybrid-engine + effort=high + image_analysis=true "
        "convierte figuras a diagramas Mermaid. Tiempo: 30-120s. Docs >50 páginas: "
        "preferir submit_parse_task."
    ),
)
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
        path, is_temp = _resolve_input_file(file_path, file_base64, file_name)
    except ValueError as e:
        return f"Error: {e}"

    if _MINERU_IS_EXTERNAL:
        return (f"BLOQUEADO por seguridad: MINERU_URL apunta a {MINERU_URL} (servidor externo). "
                "Configurar MINERU_URL a localhost:8000 o una URL interna.")

    gpu_err = ensure_gpu_for_mineru(backend)
    if gpu_err:
        return f"Error liberando GPU: {gpu_err}"

    try:
        form = _build_form(backend, parse_method, effort, lang, formula_enable, table_enable, image_analysis)
        if start_page is not None:
            form["start_page_id"] = str(int(start_page))
        if end_page is not None:
            form["end_page_id"] = str(int(end_page))

        async with _client(timeout=PARSE_TIMEOUT) as c:
            with open(path, "rb") as f:
                r = await c.post("/file_parse", files={"files": (path.name, f, _mime(path))}, data=form)
            r.raise_for_status()
            data = r.json()
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
        release_gpu_after_mineru()

    md = _extract_md(data, path.name)
    if not md.strip():
        return f"MinerU no extrajo contenido de {path.name}. El archivo puede estar vacío o protegido."
    meta = {"pages": data.get("pages") or data.get("total_pages"), "backend": form["backend"]}
    return _format_md_response(md, file_name or path.name, meta)


@mcp.tool(
    name="submit_parse_task",
    description=(
        "Envía un documento a MinerU para parseo ASÍNCRONO y devuelve un task_id. "
        "Usar para documentos grandes (>50 páginas). Mismos params de entrada que "
        "parse_document (file_path o file_base64+file_name). Luego get_task_status "
        "y get_task_result."
    ),
)
async def submit_parse_task(
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
        path, is_temp = _resolve_input_file(file_path, file_base64, file_name)
    except ValueError as e:
        return f"Error: {e}"

    if _MINERU_IS_EXTERNAL:
        return (f"BLOQUEADO por seguridad: MINERU_URL apunta a {MINERU_URL} (servidor externo).")

    gpu_err = ensure_gpu_for_mineru(backend)
    if gpu_err:
        return f"Error liberando GPU: {gpu_err}"

    try:
        form = _build_form(backend, parse_method, effort, lang, formula_enable, table_enable, image_analysis)
        if start_page is not None:
            form["start_page_id"] = str(int(start_page))
        if end_page is not None:
            form["end_page_id"] = str(int(end_page))

        async with _client(timeout=30.0) as c:
            with open(path, "rb") as f:
                r = await c.post("/tasks", files={"files": (path.name, f, _mime(path))}, data=form)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    finally:
        if is_temp:
            path.unlink(missing_ok=True)
        release_gpu_after_mineru()

    task_id = data.get("task_id") or data.get("id") or "?"
    return (f"Tarea enviada exitosamente.\ntask_id: {task_id}\narchivo: {file_name or path.name}\n"
            f"backend: {form['backend']}\n\nUsar get_task_status(task_id) para saber cuándo terminó.")


@mcp.tool(
    name="get_task_status",
    description="Consulta el estado de una tarea asíncrona de MinerU (pending/processing/completed/failed).",
)
async def get_task_status(task_id: str) -> str:
    try:
        async with _client() as c:
            r = await c.get(f"/tasks/{task_id}")
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"

    status = data.get("status", "unknown")
    progress = data.get("progress") or data.get("percentage")
    message = data.get("message") or data.get("error") or ""
    lines = [f"task_id: {task_id}", f"status: {status}"]
    if progress is not None:
        lines.append(f"progreso: {progress}%")
    if message:
        lines.append(f"mensaje: {message}")
    if status == "completed":
        lines.append("\nListo. Usar get_task_result(task_id).")
    elif status == "failed":
        lines.append("\nError en el parseo.")
    elif status in ("pending", "processing"):
        lines.append("\nEn proceso.")
    return "\n".join(lines)


@mcp.tool(
    name="get_task_result",
    description="Obtiene el Markdown de una tarea asíncrona COMPLETADA (llamar después de que get_task_status devuelva 'completed').",
)
async def get_task_result(task_id: str) -> str:
    try:
        async with _client(timeout=30.0) as c:
            status_r = await c.get(f"/tasks/{task_id}")
            status_r.raise_for_status()
            status_data = status_r.json()
            if status_data.get("status") != "completed":
                return (f"La tarea {task_id} aún no está completada "
                        f"(estado: {status_data.get('status', 'unknown')}).")
            result_r = await c.get(f"/tasks/{task_id}/result")
            result_r.raise_for_status()
            data = result_r.json()
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"

    md = _extract_md(data, task_id)
    if not md.strip():
        return f"La tarea {task_id} completó pero no devolvió contenido."
    filename = data.get("filename") or task_id
    meta = {"pages": data.get("pages") or data.get("total_pages"), "backend": data.get("backend")}
    return _format_md_response(md, filename, meta)


@mcp.tool(
    name="mineru_health",
    description="Verifica que MinerU esté disponible: versión, tareas en cola, workers activos.",
)
async def mineru_health() -> str:
    try:
        async with _client(timeout=10.0) as c:
            r = await c.get("/health")
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        return f"Error: no se puede contactar MinerU en {MINERU_URL}: {type(e).__name__}: {e}"

    status = data.get("status", "unknown")
    queue = data.get("queue_depth") or data.get("pending_tasks", 0)
    workers = data.get("workers") or data.get("active_workers", "?")
    version = data.get("version") or data.get("mineru_version", "?")
    lines = [
        f"MinerU está {'disponible' if status in ('ok', 'healthy') else 'degradado'}.",
        f"URL: {MINERU_URL}",
    ]
    if _MINERU_IS_EXTERNAL:
        lines.append("ADVERTENCIA: MINERU_URL apunta a un servidor EXTERNO.")
    lines += [f"Status: {status}", f"Versión: {version}", f"Tareas en cola: {queue}", f"Workers activos: {workers}"]
    return "\n".join(lines)


# ─── Entry point ──────────────────────────────────────────────────────────

def main():
    use_stdio = "--stdio" in sys.argv or os.getenv("MCP_TRANSPORT") == "stdio"
    port = int(os.getenv("MCP_PORT", "8202"))
    host = os.getenv("MCP_HOST", "0.0.0.0")

    if use_stdio:
        mcp.run(transport="stdio")
    else:
        app = mcp.http_app(stateless_http=True)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
