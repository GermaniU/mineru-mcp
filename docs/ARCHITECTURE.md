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
                           | Loopback HTTP REST (Puerto 8002)
                           v
 +-------------------------------------------------------------------+
 |                         MinerU API Engine                         |
 |  (PDF-Extract-Kit + MinerU2.5-VLM + PyTorch + CUDA/CPU Pipeline)  |
 +-------------------------------------------------------------------+
                                  |
                                  | Retorna Markdown / Tablas / Fórmulas / Imágenes
                                  v
 +-------------------------------------------------------------------+
 |                      Estructura JSON Devuelta                     |
 |        { "markdown": "...", "images": [...], "formulas": [...] }  |
 +-------------------------------------------------------------------+
```

---

## 🧩 Componentes Principales

### 1. FastMCP Server (`src/mineru_mcp/server.py`)
- Expone endpoints HTTP y SSE bajo el protocolo Model Context Protocol (MCP) en el puerto `8202`.
- Declara e inicia las herramientas expuestas (`parse_pdf`, `get_task_status`, `list_tasks`, `mineru_health`).
- Maneja el ciclo de vida del servidor Uvicorn / Starlette.

### 2. MinerU Client (`src/mineru_mcp/mineru_client.py`)
- Cliente HTTP asíncrono liviano sobre `httpx`.
- Traduce llamadas MCP en invocaciones a la REST API interna de `mineru-api`:
  - `GET /health` — Monitoreo de disponibilidad del motor de extracción.
  - `POST /file/extract` / `POST /url/extract` — Encolamiento y ejecución de extracción de PDFs.
  - `GET /task/{task_id}` — Polling del estado de parsing de documentos pesados.

### 3. Helpers de Procesamiento de Entrada (`src/mineru_mcp/helpers.py`)
- Procesa de forma transparente las dos modalidades de entrada de documentos:
  - **Path Local**: Si el archivo PDF ya reside en el servidor host (`file_path`).
  - **Base64 Remoto**: Si el cliente remoto envía el archivo codificado en Base64 (`file_base64` + `file_name`), decodificándolo y almacenándolo temporalmente en `/tmp/mineru_uploads/`.

### 4. GPU Arbiter (`src/mineru_mcp/gpu_arbiter.py`)
- Coordina el uso de memoria VRAM en servidores con GPUs compartidas (ej. NVIDIA RTX 3060 de 12GB).
- Si la solicitud especifica backend `hybrid-engine` o `vlm-engine` (~4GB VRAM), el arbiter asegura la disponibilidad de VRAM realizando la transición de servicios mediante systemd (`llama-server` / `comfyui`).
- Si el backend es `pipeline` (CPU, default), no toca la GPU ni conmuta servicios.

---

## 🔄 Flujo de Datos (`parse_pdf`)

1. **Recepción**: El cliente MCP envía una solicitud a la tool `parse_pdf` en `http://<HOST>:8202/mcp`.
2. **Procesamiento de Entrada**: `helpers.py` valida la ruta local o decodifica el Base64 en `/tmp/mineru_uploads/`.
3. **Arbitraje GPU**: Si se especifica un backend VLM/GPU, `gpu_arbiter.py` verifica y asegura la VRAM antes de llamar a la API.
4. **Extracción**: `mineru_client.py` envía la solicitud a `POST http://127.0.0.1:8002/file/extract`.
5. **Respuesta**: MinerU retorna el documento parseado con sintaxis Markdown estructurada, código LaTeX para fórmulas matemáticas, tablas extractadas y paths/URLs de imágenes extraídas.

---

## 🔒 Red y Seguridad

- **Loopback Interno**: `mineru-api` escucha en `127.0.0.1:8002` para evitar exponer la API interna sin autenticar a la red externa.
- **MCP LAN Binding**: El MCP server escucha en `0.0.0.0:8202`, protegido por reglas UFW del host (`ufw allow from <YOUR_LAN_CIDR>`).
