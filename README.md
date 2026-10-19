<p align="center">
  <img src="docs/assets/og-image.png" alt="MinerU MCP — Extracción y parseo de PDFs para agentes IA vía Model Context Protocol" width="720">
</p>

[English](README.en.md) · **Español**

# MinerU MCP — Extracción y parseo de PDFs para agentes IA vía Model Context Protocol (MCP)

> **Transforma cualquier documento PDF en Markdown estructurado, tablas y código LaTeX para tus agentes IA.**
> Servidor MCP open source que expone las capacidades de extracción de MinerU (`PDF-Extract-Kit` / `MinerU2.5-VLM`) a Claude Code, Cursor, Windsurf, Hermes Gateway y cualquier cliente compatible con [Model Context Protocol](https://modelcontextprotocol.io). FastMCP HTTP/SSE + soporte para path local o Base64, **cero dependencias en clientes, 100% en tu hardware**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Streamable_HTTP%2FSSE-green)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![CI](https://github.com/GermaniU/mineru-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/GermaniU/mineru-mcp/actions/workflows/ci.yml)
[![FastMCP](https://img.shields.io/badge/FastMCP-v2.0+-purple.svg)](https://github.com/jlowin/fastmcp)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**Tags:** `mcp-server` · `mineru` · `pdf-parser` · `ocr` · `latex` · `ai-agents` · `fastmcp` · `claude-code` · `cursor` · `hermes-gateway` · `local-first` · `self-hosted`

---

## 💡 Por qué existe

Extraer texto estructurado, tablas complejas y fórmulas matemáticas de archivos PDF suele requerir entornos Python pesados con PyTorch, OCR y modelos de visión en cada máquina cliente. **MinerU MCP** resuelve esto actuando como un adaptador middleware HTTP/SSE desacoplado:

- 🚀 **Cero Instalación Local**: Cualquier cliente MCP procesa documentos vía HTTP/SSE en puerto `8202` pasando un `file_path` local o enviando el PDF codificado en `file_base64`.
- 📊 **Markdown Estructurado y LaTeX**: Convierte encabezados, listas, tablas complejas y ecuaciones matemáticas en código LaTeX estándar listo para RAG.
- 🧠 **Ejecución Flexible (CPU / GPU VRAM)**: Pipeline por defecto en CPU sin tocar VRAM, o aceleración VLM opcional coordinada con el GPU Arbiter.

---

## 🏗️ Arquitectura y Deslinde de Componentes

> ⚠️ **IMPORTANTE: Entender los Límites del Sistema**
>
> `mineru-mcp` es **únicamente la capa de transporte e interfaz MCP**. No incluye el motor de procesamiento `mineru-api` ni la descarga en caché de modelos de HuggingFace.
> Para la guía de despliegue del servidor backend en el host Linux/Pop!_OS, consulta [docs/SERVER_SETUP.md](docs/SERVER_SETUP.md) y [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
 +-------------------------------------------------------+
 |                 Clientes MCP (LAN)                    |
 | (Claude Code CLI / Cursor / Windsurf / Hermes Gateway)|
 +-------------------------------------------------------+
                             |
                             | HTTP / SSE (Puerto 8202)
                             v
 +-------------------------------------------------------+
 |                   mineru-mcp Server                   |
 |        (FastMCP + File Path / Base64 Decoder)         |
 +-------------------------------------------------------+
                             |
                             | Loopback HTTP (Puerto 8000)
                             v
 +-------------------------------------------------------+
 |                  MinerU Backend Host                  |
 |  (mineru-api + PDF-Extract-Kit + HuggingFace Cache)   |
 +-------------------------------------------------------+
```

---

## 📦 Instalación Rápida

### Requisitos
- Python 3.11+
- `uv` (recomendado) o `pip`

### Clonar e Instalar

```bash
git clone https://github.com/GermaniU/mineru-mcp.git
cd mineru-mcp

# Crear entorno virtual e instalar
uv venv
source .venv/bin/activate
uv pip install -e .
```

### Con Docker (stdio, sin clonar)

La imagen `ghcr.io/germaniu/mineru-mcp` habla MCP por stdio y llama a un `mineru-api` que corre en el host. Configúrala en tu cliente MCP:

```json
{
  "mcpServers": {
    "mineru": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "--add-host", "host.docker.internal:host-gateway",
        "-e", "MINERU_URL=http://host.docker.internal:8000",
        "ghcr.io/germaniu/mineru-mcp:latest", "--stdio"
      ]
    }
  }
}
```

Dentro del contenedor `file_path` se refiere al sistema de archivos del contenedor: manda los documentos con `file_base64` + `file_name`, o monta un directorio con `-v`. Sin systemd en el contenedor no hay wake-on-demand ni GPU Broker: `mineru-api` tiene que estar ya arriba.

---

## ⚙️ Configuración (Variables de Entorno)

Crea un archivo `.env` o exporta las siguientes variables:

| Variable | Valor por Defecto | Descripción |
|----------|-------------------|-------------|
| `MINERU_URL` | `http://127.0.0.1:8000` | URL de `mineru-api`. Solo se aceptan loopback y `host.docker.internal`; con cualquier otro host las tools se niegan a enviar documentos. |
| `MINERU_BACKEND` | `pipeline` | Backend si la llamada lo deja vacío (`pipeline`, `hybrid-engine`, `vlm-engine`). |
| `MINERU_PARSE_METHOD` | `auto` | Método de extracción si la llamada lo deja vacío (`auto`, `txt`, `ocr`). |
| `MINERU_LANG` | `es` | Idioma OCR si la llamada lo deja vacío. |
| `MCP_HOST` | `0.0.0.0` | Host binding del modo HTTP. |
| `MCP_PORT` | `8202` | Puerto del modo HTTP. |
| `MCP_AUTH_TOKEN` | *(vacío = sin auth)* | Si se define, el modo HTTP exige `Authorization: Bearer <token>` en cada request. |
| `MCP_TRANSPORT` | *(vacío = HTTP)* | `stdio` equivale a pasar `--stdio`. |

Qué protege y qué no cada ajuste: [SECURITY.md](SECURITY.md).

---

## 🛠️ Herramientas Expuestas (Tool Reference)

| Tool | Qué hace |
|------|----------|
| `parse_document` | Parseo síncrono (30-120 s) de PDF, DOCX, PPTX, XLSX o imagen a Markdown. Entrada: `file_path` (ruta en el server) o `file_base64` + `file_name`. Opcionales: `backend`, `effort`, `image_analysis`, `parse_method`, `lang`, `formula_enable`, `table_enable`, `start_page`, `end_page`. |
| `submit_parse_task` | Igual que `parse_document` pero asíncrono: devuelve un `task_id`. Para documentos de más de ~50 páginas. |
| `get_task_status` | Estado de una tarea (`pending` / `processing` / `completed` / `failed`). |
| `get_task_result` | Markdown de una tarea ya completada. |
| `mineru_health` | Disponibilidad de `mineru-api`, versión y tareas en cola. |

`hybrid-engine` + `effort=high` + `image_analysis=true` convierte figuras en diagramas Mermaid.

---

## 🧭 ¿Y los otros servidores MCP para documentos?

Hay tres familias, y resuelven problemas distintos.

| | **MinerU MCP** (este) | MCP oficial de MinerU (cloud) | Conversores generales (Docling, MarkItDown) |
|---|---|---|---|
| Dónde se parsea | Tu `mineru-api`, en tu hardware | La API cloud de MinerU | La máquina donde corre el MCP |
| Tus documentos salen de tu red | **No** (bloquea URLs externas) | Sí | No |
| Cuenta / token | Ninguno | Token de la API de MinerU | Ninguno |
| Dependencias en el cliente | Ninguna (HTTP) o solo Docker (stdio) | Python (`uvx mineru-open-mcp`) | El motor de conversión completo |
| Comparte la GPU con un LLM local | **Sí** (GPU Broker) | N/A | No |
| Motor | MinerU (`pipeline` / `vlm` / `hybrid`) | MinerU | El suyo propio |

**En una frase:**
- Si no tienes GPU ni servidor y no te importa subir los documentos → el MCP cloud oficial de MinerU.
- Si quieres un conversor que viva en la misma máquina que el cliente → Docling o MarkItDown.
- Si ya tienes (o quieres) MinerU en tu propio servidor y que **los documentos no salgan de tu red**, compartido por todos los clientes de la LAN → este.

---

## 🔗 Integración con Clientes MCP

### Configuración para Claude Code CLI (`~/.claude.json`)

```json
{
  "mcpServers": {
    "mineru": {
      "url": "http://<YOUR_SERVER_IP>:8202/mcp"
    }
  }
}
```

### Configuración para Hermes Gateway (`~/.hermes/config.yaml`)

```yaml
mcp_servers:
  mineru:
    url: "http://<YOUR_SERVER_IP>:8202/mcp"
    transport: "http"
```

### Configuración para Cursor / Windsurf / Claude Desktop

Añade un servidor MCP de tipo **SSE / HTTP** con la URL `http://<LAN_IP>:8202/mcp`.

---

## 📋 Componentes Faltantes y Roadmap (Server Gaps)

Dado que este repo representa la **capa MCP**, los siguientes elementos están fuera de este repositorio y deben configurarse en el servidor host:

1. **Paquete `mineru-api`**: Requiere instalación independiente de `mineru==3.4.4` en la máquina host Linux.
2. **Caché de Modelos HuggingFace**: Modelos `PDF-Extract-Kit` alojados en `~/.cache/huggingface`.
3. **Servicios Systemd**: Manifiestos `mineru-api.service` y `mineru-mcp.service`.
4. **Futuras Mejoras del MCP**:
   - Streaming parcial de fragmentos Markdown durante extracciones extensas.
   - Limpieza automática programada del directorio de descargas `/tmp/mineru_uploads/`.

---

## 🧪 Pruebas Unitarias

```bash
uv run --with pytest --with pytest-asyncio pytest
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo [LICENSE](LICENSE) para más detalles.
