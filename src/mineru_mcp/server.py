"""FastMCP server + entry point (stdio/HTTP)."""

import os
import sys

import uvicorn
from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from .tools.health import mineru_health
from .tools.parse import parse_document
from .tools.tasks import get_task_result, get_task_status, submit_parse_task

mcp = FastMCP("mineru")


class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = os.getenv("MCP_AUTH_TOKEN")
        if token:
            header = request.headers.get("authorization", "")
            expected = f"Bearer {token}"
            if header != expected:
                return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


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
async def _parse_document(
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
    return await parse_document(
        file_path=file_path,
        file_base64=file_base64,
        file_name=file_name,
        backend=backend,
        effort=effort,
        image_analysis=image_analysis,
        parse_method=parse_method,
        lang=lang,
        formula_enable=formula_enable,
        table_enable=table_enable,
        start_page=start_page,
        end_page=end_page,
    )


@mcp.tool(
    name="submit_parse_task",
    description=(
        "Envía un documento a MinerU para parseo ASÍNCRONO y devuelve un task_id. "
        "Usar para documentos grandes (>50 páginas). Mismos params de entrada que "
        "parse_document (file_path o file_base64+file_name). Luego get_task_status "
        "y get_task_result."
    ),
)
async def _submit_parse_task(
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
    return await submit_parse_task(
        file_path=file_path,
        file_base64=file_base64,
        file_name=file_name,
        backend=backend,
        effort=effort,
        image_analysis=image_analysis,
        parse_method=parse_method,
        lang=lang,
        formula_enable=formula_enable,
        table_enable=table_enable,
        start_page=start_page,
        end_page=end_page,
    )


@mcp.tool(
    name="get_task_status",
    description="Consulta el estado de una tarea asíncrona de MinerU (pending/processing/completed/failed).",
)
async def _get_task_status(task_id: str) -> str:
    return await get_task_status(task_id)


@mcp.tool(
    name="get_task_result",
    description="Obtiene el Markdown de una tarea asíncrona COMPLETADA (llamar después de que get_task_status devuelva 'completed').",
)
async def _get_task_result(task_id: str) -> str:
    return await get_task_result(task_id)


@mcp.tool(
    name="mineru_health",
    description="Verifica que MinerU esté disponible: versión, tareas en cola, workers activos.",
)
async def _mineru_health() -> str:
    return await mineru_health()


def main():
    use_stdio = "--stdio" in sys.argv or os.getenv("MCP_TRANSPORT") == "stdio"
    port = int(os.getenv("MCP_PORT", "8202"))
    host = os.getenv("MCP_HOST", "0.0.0.0")

    if use_stdio:
        mcp.run(transport="stdio")
    else:
        app = mcp.http_app(stateless_http=True)
        app.add_middleware(BearerAuthMiddleware)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
