# Arquitectura de `mineru-mcp`

`mineru-mcp` es un **servidor MCP HTTP/SSE** desacoplado que actúa como adaptador middleware entre clientes MCP (Claude Desktop, Claude Code CLI, Cursor, Windsurf, Hermes Gateway) y el motor de extracción de PDFs y documentos **MinerU** (`mineru-api`).

---

## 🏗️ Visión General de la Arquitectura

```
 +-------------------------------------------------------------------+
 |                      MCP Clients / Gateways                       |
 |    (Claude Desktop / Cursor / Windsurf / Hermes Gateway LAN)      |
 +-------------------------------------------------------------------+
                                  |
                                  | HTTP / SSE (Puerto 8202)
                                  v
 +-------------------------------------------------------------------+
 |                          mineru-mcp Server                        |
 |                                                                   |
 |  +--------------------+  +--------------------+  +-------------+  |
 |  | FastMCP Server     |  | GPU Arbiter Client |  | Helpers     |  |
 |  | (server.py)        |  | (gpu_arbiter.py)   |  | (helpers.py)|  |
 |  +--------------------+  +--------------------+  +-------------+  |
 |            |                        |                           |
 |            +------------+-----------+                           |
 |                         | HTTP Client                           |
 |                         v                                       |
 |             +------------------------+                          |
 |             | MinerUClient           |                          |
 |             | (mineru_client.py)     |                          |
 |             +------------------------+                          |
 +-------------------------------------------------------------------+
                           |
                           | Loopback HTTP REST (Puerto 8000)
                           v
 +-------------------------------------------------------------------+
 |                         MinerU API Engine                         |
 |  (PDF-Extract-Kit + MinerU2.5-VLM + PyTorch + CUDA/CPU Pipeline)  |
 +-------------------------------------------------------------------+
                                  |
                                  | Retorna Markdown con tablas y fórmulas
                                  v
 +-------------------------------------------------------------------+
 |                      Estructura JSON Devuelta                     |
 |        { "results": { "<archivo>": { "md_content": "..." } } }    |
 +-------------------------------------------------------------------+
```

---

## 🧩 Componentes Principales

### 1. FastMCP Server (`src/mineru_mcp/server.py`)
- Expone endpoints HTTP y SSE bajo el protocolo Model Context Protocol (MCP) en el puerto `8202`.
- Declara e inicia las herramientas expuestas (`parse_document`, `submit_parse_task`, `get_task_status`, `get_task_result`, `mineru_health`); cada una vive en `src/mineru_mcp/tools/`.
- En `initialize` anuncia como `serverInfo.version` la versión del paquete `mineru-mcp`.
- Maneja el ciclo de vida del servidor Uvicorn / Starlette.

### 2. MinerU Client (`src/mineru_mcp/mineru_client.py`)
- Cliente HTTP asíncrono liviano sobre `httpx`.
- Traduce llamadas MCP en invocaciones a la REST API interna de `mineru-api`:
  - `GET /health` — Monitoreo de disponibilidad del motor de extracción.
  - `POST /file_parse` — Parseo síncrono (`parse_document`).
  - `POST /tasks` — Encola una tarea asíncrona (`submit_parse_task`).
  - `GET /tasks/{task_id}` y `GET /tasks/{task_id}/result` — Estado y Markdown de la tarea.
- Si `mineru-api` no responde y hay systemd, lo arranca (`systemctl --user start`, o `systemctl start` con `MINERU_SYSTEMCTL_SCOPE=system`) y espera hasta 90 s antes de parsear.

### 3. Helpers de Procesamiento de Entrada (`src/mineru_mcp/helpers.py`)
- Procesa de forma transparente las dos modalidades de entrada de documentos:
  - **Path Local**: Si el archivo PDF ya reside en el servidor host (`file_path`).
  - **Base64 Remoto**: Si el cliente remoto envía el archivo codificado en Base64 (`file_base64` + `file_name`), decodificándolo en un archivo temporal del sistema que se borra al terminar el parseo.

### 4. GPU Arbiter (`src/mineru_mcp/gpu_arbiter.py`)
- Coordina el uso de memoria VRAM en servidores con GPUs compartidas (ej. NVIDIA RTX 3060 de 12GB).
- Antes de cada parseo pide la VRAM al GPU Broker del host (`gpu-broker.sh need mineru <MiB> <client_id>`): ~1.5 GB para `pipeline` (default; sus modelos de layout/OCR también usan la GPU) y ~4 GB para `hybrid-engine` / `vlm-engine`. Al terminar el trabajo real la libera con el mismo `client_id`, y el broker solo restaura otros servicios (p. ej. `llama-server`) cuando no quedan holders.
- Sin broker instalado, el fallback detiene ComfyUI si está activo; sin systemd (Docker) no hace nada.

---

## 🔄 Flujo de Datos (`parse_document`)

1. **Recepción**: El cliente MCP envía una solicitud a la tool `parse_document` en `http://<HOST>:8202/mcp`.
2. **Procesamiento de Entrada**: `helpers.py` valida la ruta local o decodifica el Base64 en un archivo temporal.
3. **Arbitraje GPU**: `mineru_client.ensure_running()` despierta `mineru-api` si hace falta y `gpu_arbiter.py` asegura la VRAM antes de llamar a la API.
4. **Extracción**: `mineru_client.py` envía el archivo a `POST {MINERU_URL}/file_parse`.
5. **Respuesta**: MinerU retorna el documento parseado con sintaxis Markdown estructurada, código LaTeX para fórmulas matemáticas y tablas en HTML. Las imágenes no se piden (`return_images=false`).

---

## 🔒 Red y Seguridad

- **Loopback Interno**: `mineru-api` escucha en loopback (`127.0.0.1:8000` por defecto) para evitar exponer la API interna sin autenticar a la red externa. Si `MINERU_URL` no es loopback, las tools se niegan a enviar documentos.
- **MCP LAN Binding**: El MCP server escucha en `0.0.0.0:8202`, protegido por reglas UFW del host (`ufw allow from <YOUR_LAN_CIDR>`).
