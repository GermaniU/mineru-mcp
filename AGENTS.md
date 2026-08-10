# AGENTS.md — mineru-mcp

MCP HTTP/SSE server que wrappea MinerU para parsing de documentos (PDF, DOCX, PPTX, XLSX, imágenes) a Markdown estructurado. Corre en Pop!_OS junto con mineru-api (puerto 8000) y expone tools vía HTTP en el puerto 8202. Cualquier gateway Hermes de la LAN lo consume sin instalar nada localmente.

## Stack

- Python 3.12+, `fastmcp`, `httpx`, `uvicorn`, `starlette`
- MinerU API en `http://127.0.0.1:8000` (loopback, misma máquina)
- GPU Broker (`~/stack/gpu-broker/gpu-broker.sh`) coordina la GPU con llama-server/ComfyUI

## Estructura (vertical slice + clean)

```
src/mineru_mcp/
├── config.py          # env vars, constantes, validaciones
├── mineru_client.py   # HTTP client thin a mineru-api (file_parse, tasks, health)
├── gpu_arbiter.py     # ensure_gpu_for_mineru + release (solo backends GPU)
├── helpers.py         # build_form, extract_md, format_md_response, resolve_input_file
├── tools/             # parse_document, submit_parse_task, get_task_status, get_task_result, mineru_health
│   ├── __init__.py
│   ├── parse.py
│   ├── tasks.py
│   └── health.py
└── server.py          # FastMCP + entry point (stdio/HTTP)
tests/                 # pytest por módulo
```

## Reglas de estilo

- Cambios chicos y directos. Tocar el camino de código más angosto que explica el problema.
- Cambiar la menor cantidad de archivos posible.
- Preferir fixes prácticos sobre arquitectura amplia. Abstracciones solo cuando quitan lógica repetida real.
- Preferir menos dependencias. No agregar deps a menos que sean necesarias.
- Borrar código obsoleto agresivamente. Sin ramas muertas, sin funciones nunca llamadas.
- Preservar APIs existentes, nombres de tools y compatibilidad de workflows.
- **El código debe verse hand-written.** Cambios que lean como código genérico de IA serán rechazados: capas helper innecesarias, nombres vagos, comentarios boilerplate, ramas defensivas sin failure mode real, rewrites amplios.

## Tools actuales

| Tool | Descripción |
|------|-------------|
| `parse_document` | Parseo síncrono (~30-120s). Docs cortos. |
| `submit_parse_task` | Asíncrono, devuelve `task_id`. Docs grandes (>50 págs). |
| `get_task_status` / `get_task_result` | Monitoreo y resultado de tareas asíncronas. |
| `mineru_health` | Verifica servidor y métricas. |

## Backends

| Backend | Cuándo | Notas |
|---|---|---|
| `pipeline` | Default, rápido, sin GPU | No compite por VRAM |
| `vlm-engine` | Máxima precisión por página | ~4GB VRAM |
| `hybrid-engine` | Mejor balance | Con `effort=high` + `image_analysis=true` da diagramas Mermaid |

## Configuración (env vars)

| Env var | Default | Descripción |
|---------|---------|-------------|
| `MINERU_URL` | `http://127.0.0.1:8000` | URL de mineru-api |
| `MINERU_BACKEND` | `pipeline` | Backend default |
| `MINERU_PARSE_METHOD` | `auto` | Método de extracción |
| `MINERU_LANG` | `es` | Idioma OCR |
| `MCP_PORT` | `8202` | Puerto del MCP server |
| `MCP_HOST` | `0.0.0.0` | Host binding |

## Seguridad

- Si `MINERU_URL` apunta a un servidor externo (no localhost/interna), el MCP **bloquea el envío** de documentos.
- Backends GPU (hybrid/vlm) coordinan con el GPU Broker antes de parsear.

## Deploy

- systemd: `mineru-mcp.service` (puerto 8202)
- El servicio corre desde el repo (`~/Sites/mineru-mcp/.venv`), WorkingDirectory = repo.
- GPU Broker en `ExecStartPre` del service para el switch de GPU.

## Flujo de trabajo

1. Rama desde `master`: `git checkout master && git pull && git checkout -b feature/...`
2. Implementar siguiendo la estructura de `src/mineru_mcp/`
3. Tests pytest por módulo
4. Commit con prefijo (`feat:`, `fix:`, `chore:`)
5. PR sin merge
6. Verificar con `pytest` antes de reportar
