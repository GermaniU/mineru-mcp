#!/usr/bin/env python3
"""
MCP stdio server que expone MinerU como herramienta de parsing de documentos.

MinerU convierte PDFs, DOCX, PPTX, XLSX e imágenes a Markdown + JSON estructurado.
El agente puede usar este MCP para extraer contenido de documentos antes de indexarlos
o responder preguntas sobre su contenido.

Tools expuestas:
  parse_document         parseo síncrono: devuelve Markdown directamente (~30-120s)
  submit_parse_task      envío asíncrono: devuelve task_id para docs grandes
  get_task_status        consulta estado de una tarea asíncrona
  get_task_result        obtiene el Markdown de una tarea completada
  mineru_health          verifica que el servidor MinerU esté vivo

Configuración (vars de entorno):
  MINERU_URL             URL base del servidor MinerU  (default: http://localhost:8000)
  MINERU_BACKEND         backend de parseo:
                           pipeline   = rápido, sin GPU, multi-idioma (recomendado para producción)
                           vlm-engine = más preciso, usa VLM propio de MinerU localmente (requiere VRAM)
                         NO usar vlm-http-client con Ollama — requiere el VLM fine-tuneado de MinerU.
  MINERU_PARSE_METHOD    método de extracción: auto | txt | ocr  (default: auto)

Iniciar servidor:
  # pipeline (recomendado, sin GPU):
  mineru-api --host 127.0.0.1 --port 8000

  # vlm-engine (más preciso, usa ~4GB VRAM adicional):
  mineru-api --host 127.0.0.1 --port 8000
  # luego en cada request: backend=vlm-engine
"""
import asyncio
import mimetypes
import os
from pathlib import Path

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

MINERU_URL = os.getenv("MINERU_URL", "http://localhost:8000").rstrip("/")
DEFAULT_BACKEND = os.getenv("MINERU_BACKEND", "pipeline")

# Aviso temprano si MINERU_URL apunta fuera de localhost — los documentos
# se enviarían a esa URL. En producción solo usar URLs internas/privadas.
_LOCAL_PREFIXES = ("http://localhost", "http://127.0.0.1", "http://0.0.0.0", "http://host.docker.internal")
_MINERU_IS_EXTERNAL = not any(MINERU_URL.startswith(p) for p in _LOCAL_PREFIXES)
DEFAULT_PARSE_METHOD = os.getenv("MINERU_PARSE_METHOD", "auto")
DEFAULT_LANG = os.getenv("MINERU_LANG", "es")

PARSE_TIMEOUT = 300.0   # 5 min para docs grandes en modo síncrono
DEFAULT_TIMEOUT = 15.0

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".png", ".jpg", ".jpeg"}

server = Server("mineru-mcp")


# ─── Helpers ──────────────────────────────────────────────────────────────

def _ok(text: str) -> list[TextContent]:
    return [TextContent(type="text", text=text)]


def _err(prefix: str, e: Exception) -> list[TextContent]:
    return _ok(f"Error {prefix}: {type(e).__name__}: {e}")


def _client(timeout: float = DEFAULT_TIMEOUT) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=MINERU_URL, timeout=timeout)


def _resolve_path(file_path: str) -> Path:
    """Resuelve rutas Windows (C:\\...) o WSL (/mnt/c/...) a Path local."""
    p = file_path.strip()
    # Ruta Windows con backslash o drive letter → convertir a WSL
    if len(p) >= 2 and p[1] == ":" :
        drive = p[0].lower()
        rest = p[2:].replace("\\", "/").lstrip("/")
        return Path(f"/mnt/{drive}/{rest}")
    return Path(p)


def _mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


_SUPPORTED_LANGS = {"ch", "ch_server", "korean", "ta", "te", "ka", "th", "el", "arabic", "east_slavic", "cyrillic", "devanagari"}

def _build_form(args: dict) -> dict:
    """Construye los campos de formulario (data) para la petición multipart."""
    form: dict = {
        "backend": args.get("backend") or DEFAULT_BACKEND,
        "parse_method": args.get("parse_method") or DEFAULT_PARSE_METHOD,
        "effort": args.get("effort") or "medium",
        "formula_enable": str(args.get("formula_enable", True)).lower(),
        "table_enable": str(args.get("table_enable", True)).lower(),
        "image_analysis": str(args.get("image_analysis", False)).lower(),
        "return_md": "true",
        "return_content_list": "false",
        "return_middle_json": "false",
        "return_images": "false",
        "response_format_zip": "false",
    }
    # Solo agregar lang_list si es un idioma con script no-latino soportado por MinerU
    lang = (args.get("lang") or DEFAULT_LANG).strip()
    if lang in _SUPPORTED_LANGS:
        form["lang_list"] = lang
    return form


def _extract_md(data: dict, filename: str) -> str:
    """Extrae el Markdown del JSON de respuesta de MinerU."""
    # Formato real: {"backend": "...", "results": {"stem": {"md_content": "..."}}}
    if "results" in data and isinstance(data["results"], dict):
        for _name, content in data["results"].items():
            if isinstance(content, dict):
                md = content.get("md_content") or content.get("md", "")
                if md:
                    return md
    # Formatos alternativos
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


# ─── Tool definitions ─────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="parse_document",
            description=(
                "Parsea un documento (PDF, DOCX, PPTX, XLSX, imagen) con MinerU y devuelve "
                "su contenido como Markdown bien estructurado. Incluye texto, tablas, fórmulas "
                "y títulos con jerarquía correcta. Usar cuando necesites extraer el contenido "
                "de un archivo para responder preguntas, indexarlo o resumirlo. "
                "Tiempo estimado: 30-120s dependiendo del tamaño. Para docs >50 páginas "
                "preferir submit_parse_task (asíncrono)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": (
                            "Ruta al archivo. Acepta rutas Windows (C:\\Users\\...) "
                            "o WSL (/mnt/c/Users/...). Formatos: pdf, docx, pptx, xlsx, png, jpg."
                        ),
                    },
                    "backend": {
                        "type": "string",
                        "enum": ["pipeline", "vlm-engine", "hybrid-engine"],
                        "description": "pipeline=rápido/sin GPU/multi-idioma. vlm-engine=VLM local lee la página completa (~4GB VRAM). hybrid-engine=pipeline para texto + VLM solo en bloques difíciles (tablas/gráficas) — mejor balance calidad/velocidad.",
                        "default": "pipeline",
                    },
                    "effort": {
                        "type": "string",
                        "enum": ["medium", "high"],
                        "description": "Solo para hybrid-engine: cuánto interviene el VLM. medium=rápido. high=máxima calidad y habilita image_analysis.",
                        "default": "medium",
                    },
                    "image_analysis": {
                        "type": "boolean",
                        "description": "El VLM describe las imágenes/figuras del documento como texto dentro del Markdown. Requiere backend hybrid-engine con effort=high (con effort=medium se ignora).",
                        "default": False,
                    },
                    "parse_method": {
                        "type": "string",
                        "enum": ["auto", "txt", "ocr"],
                        "description": "auto=detecta automáticamente; txt=solo texto nativo; ocr=forzar OCR.",
                        "default": "auto",
                    },
                    "lang": {
                        "type": "string",
                        "description": "Idioma(s) para OCR, separados por coma (ej: 'es', 'es,en').",
                        "default": "es",
                    },
                    "formula_enable": {
                        "type": "boolean",
                        "description": "Extraer fórmulas matemáticas como LaTeX.",
                        "default": True,
                    },
                    "table_enable": {
                        "type": "boolean",
                        "description": "Reconstruir tablas en Markdown.",
                        "default": True,
                    },
                    "start_page": {
                        "type": "integer",
                        "description": "Página de inicio (0-indexed, inclusive). Omitir para parsear desde el inicio.",
                    },
                    "end_page": {
                        "type": "integer",
                        "description": "Página de fin (0-indexed, inclusive). Omitir para parsear hasta el final.",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="submit_parse_task",
            description=(
                "Envía un documento a MinerU para parseo ASÍNCRONO y devuelve un task_id. "
                "Usar para documentos grandes (>50 páginas) donde la espera síncrona sería "
                "demasiado larga. Luego usar get_task_status para saber cuándo terminó "
                "y get_task_result para obtener el Markdown."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Ruta al archivo (Windows o WSL). Formatos: pdf, docx, pptx, xlsx, png, jpg.",
                    },
                    "backend": {
                        "type": "string",
                        "enum": ["pipeline", "vlm-engine", "hybrid-engine"],
                        "default": "pipeline",
                    },
                    "effort": {
                        "type": "string",
                        "enum": ["medium", "high"],
                        "description": "Solo hybrid-engine: high habilita image_analysis y máxima calidad.",
                        "default": "medium",
                    },
                    "image_analysis": {
                        "type": "boolean",
                        "description": "VLM describe imágenes/figuras como texto. Requiere hybrid-engine + effort=high.",
                        "default": False,
                    },
                    "parse_method": {
                        "type": "string",
                        "enum": ["auto", "txt", "ocr"],
                        "default": "auto",
                    },
                    "lang": {
                        "type": "string",
                        "default": "es",
                    },
                    "formula_enable": {"type": "boolean", "default": True},
                    "table_enable": {"type": "boolean", "default": True},
                    "start_page": {"type": "integer"},
                    "end_page": {"type": "integer"},
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="get_task_status",
            description=(
                "Consulta el estado de una tarea asíncrona de MinerU. "
                "Estados posibles: pending, processing, completed, failed. "
                "Llamar periódicamente hasta obtener 'completed' o 'failed'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID de tarea devuelto por submit_parse_task.",
                    },
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="get_task_result",
            description=(
                "Obtiene el Markdown de una tarea asíncrona COMPLETADA. "
                "Solo llamar después de que get_task_status devuelva 'completed'. "
                "Si la tarea aún no terminó, devuelve un error."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "ID de tarea completada.",
                    },
                },
                "required": ["task_id"],
            },
        ),
        Tool(
            name="mineru_health",
            description=(
                "Verifica que el servidor MinerU esté disponible y devuelve métricas "
                "del servidor (tareas en cola, workers disponibles). Usar antes de parsear "
                "si hay dudas de disponibilidad."
            ),
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


# ─── Tool handlers ────────────────────────────────────────────────────────

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "parse_document":
            return await _parse_document(arguments)
        if name == "submit_parse_task":
            return await _submit_parse_task(arguments)
        if name == "get_task_status":
            return await _get_task_status(arguments)
        if name == "get_task_result":
            return await _get_task_result(arguments)
        if name == "mineru_health":
            return await _mineru_health()
        return _ok(f"Error: tool desconocido '{name}'")
    except httpx.ConnectError:
        return _ok(
            f"Error: no se puede conectar a MinerU en {MINERU_URL}. "
            "Verificar que el servidor esté corriendo con `mineru-api`."
        )
    except httpx.TimeoutException:
        return _ok(
            "Error: timeout esperando respuesta de MinerU. "
            "El documento puede ser muy grande — intentar con submit_parse_task (asíncrono)."
        )
    except httpx.HTTPStatusError as e:
        return _ok(f"Error HTTP {e.response.status_code} en {name}: {e.response.text[:300]}")
    except Exception as e:
        return _err(f"en {name}", e)


async def _parse_document(args: dict) -> list[TextContent]:
    file_path = (args.get("file_path") or "").strip()
    if not file_path:
        return _ok("Error: file_path es obligatorio.")

    path = _resolve_path(file_path)
    if not path.exists():
        return _ok(f"Error: archivo no encontrado en {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return _ok(
            f"Error: extensión '{path.suffix}' no soportada. "
            f"Soportadas: {', '.join(SUPPORTED_EXTENSIONS)}"
        )

    if _MINERU_IS_EXTERNAL:
        return _ok(
            f"BLOQUEADO por seguridad: MINERU_URL apunta a {MINERU_URL} (servidor externo). "
            "Los documentos no se enviarán a URLs externas. "
            "Configurar MINERU_URL a localhost:8000 o una URL interna."
        )

    form = _build_form(args)
    if (sp := args.get("start_page")) is not None:
        form["start_page_id"] = str(int(sp))
    if (ep := args.get("end_page")) is not None:
        form["end_page_id"] = str(int(ep))

    async with _client(timeout=PARSE_TIMEOUT) as c:
        with open(path, "rb") as f:
            r = await c.post(
                "/file_parse",
                files={"files": (path.name, f, _mime(path))},
                data=form,
            )
        r.raise_for_status()
        data = r.json()

    md = _extract_md(data, path.name)
    if not md.strip():
        return _ok(f"MinerU no extrajo contenido de {path.name}. El archivo puede estar vacío o protegido.")

    meta = {
        "pages": data.get("pages") or data.get("total_pages"),
        "backend": form["backend"],
    }
    return _ok(_format_md_response(md, path.name, meta))


async def _submit_parse_task(args: dict) -> list[TextContent]:
    file_path = (args.get("file_path") or "").strip()
    if not file_path:
        return _ok("Error: file_path es obligatorio.")

    if _MINERU_IS_EXTERNAL:
        return _ok(
            f"BLOQUEADO por seguridad: MINERU_URL apunta a {MINERU_URL} (servidor externo). "
            "Configurar MINERU_URL a localhost:8000 o una URL interna."
        )

    path = _resolve_path(file_path)
    if not path.exists():
        return _ok(f"Error: archivo no encontrado en {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return _ok(f"Error: extensión '{path.suffix}' no soportada.")

    form = _build_form(args)
    if (sp := args.get("start_page")) is not None:
        form["start_page_id"] = str(int(sp))
    if (ep := args.get("end_page")) is not None:
        form["end_page_id"] = str(int(ep))

    async with _client(timeout=30.0) as c:
        with open(path, "rb") as f:
            r = await c.post(
                "/tasks",
                files={"files": (path.name, f, _mime(path))},
                data=form,
            )
        r.raise_for_status()
        data = r.json()

    task_id = data.get("task_id") or data.get("id") or "?"
    return _ok(
        f"Tarea enviada exitosamente.\n"
        f"task_id: {task_id}\n"
        f"archivo: {path.name}\n"
        f"backend: {form['backend']}\n\n"
        "Usar get_task_status(task_id) para saber cuándo terminó."
    )


async def _get_task_status(args: dict) -> list[TextContent]:
    task_id = (args.get("task_id") or "").strip()
    if not task_id:
        return _ok("Error: task_id es obligatorio.")

    async with _client() as c:
        r = await c.get(f"/tasks/{task_id}")
        r.raise_for_status()
        data = r.json()

    status = data.get("status", "unknown")
    progress = data.get("progress") or data.get("percentage")
    message = data.get("message") or data.get("error") or ""

    lines = [f"task_id: {task_id}", f"status: {status}"]
    if progress is not None:
        lines.append(f"progreso: {progress}%")
    if message:
        lines.append(f"mensaje: {message}")

    if status == "completed":
        lines.append("\nListo. Usar get_task_result(task_id) para obtener el Markdown.")
    elif status == "failed":
        lines.append("\nError en el parseo. Revisar el mensaje de error.")
    elif status in ("pending", "processing"):
        lines.append("\nEn proceso. Volver a consultar en unos segundos.")

    return _ok("\n".join(lines))


async def _get_task_result(args: dict) -> list[TextContent]:
    task_id = (args.get("task_id") or "").strip()
    if not task_id:
        return _ok("Error: task_id es obligatorio.")

    async with _client(timeout=30.0) as c:
        # Primero verificar que esté completada
        status_r = await c.get(f"/tasks/{task_id}")
        status_r.raise_for_status()
        status_data = status_r.json()

        if status_data.get("status") != "completed":
            current = status_data.get("status", "unknown")
            return _ok(
                f"La tarea {task_id} aún no está completada (estado: {current}). "
                "Usar get_task_status para monitorear el progreso."
            )

        # Obtener el resultado
        result_r = await c.get(f"/tasks/{task_id}/result")
        result_r.raise_for_status()
        data = result_r.json()

    md = _extract_md(data, task_id)
    if not md.strip():
        return _ok(f"La tarea {task_id} completó pero no devolvió contenido.")

    filename = data.get("filename") or status_data.get("filename") or task_id
    meta = {
        "pages": data.get("pages") or data.get("total_pages"),
        "backend": data.get("backend"),
    }
    return _ok(_format_md_response(md, filename, meta))


async def _mineru_health() -> list[TextContent]:
    async with _client(timeout=10.0) as c:
        r = await c.get("/health")
        r.raise_for_status()
        data = r.json()

    status = data.get("status", "unknown")
    queue = data.get("queue_depth") or data.get("pending_tasks", 0)
    workers = data.get("workers") or data.get("active_workers", "?")
    version = data.get("version") or data.get("mineru_version", "?")

    lines = [
        f"MinerU está {'disponible' if status in ('ok', 'healthy') else 'degradado'}.",
        f"URL: {MINERU_URL}",
    ]
    if _MINERU_IS_EXTERNAL:
        lines.append(
            "ADVERTENCIA: MINERU_URL apunta a un servidor EXTERNO. "
            "Los documentos que parsees serán enviados a esa URL."
        )
    lines += [
        f"Status: {status}",
        f"Versión: {version}",
        f"Tareas en cola: {queue}",
        f"Workers activos: {workers}",
    ]
    return _ok("\n".join(lines))


# ─── Entry point ──────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
