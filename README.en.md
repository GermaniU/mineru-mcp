<p align="center">
  <img src="docs/assets/og-image.png" alt="MinerU MCP — PDF Extraction & Parsing for AI Agents via Model Context Protocol" width="720">
</p>

**English** · [Español](README.md)

# MinerU MCP — PDF Extraction & Parsing for AI Agents via Model Context Protocol (MCP)

> **Transform any PDF document into structured Markdown, tables, and LaTeX equations for your AI agents.**
> Open-source MCP server exposing MinerU extraction capabilities (`PDF-Extract-Kit` / `MinerU2.5-VLM`) to Claude Code, Cursor, Windsurf, Hermes Gateway, and any client compatible with [Model Context Protocol](https://modelcontextprotocol.io). FastMCP HTTP/SSE + local file path or Base64 payload support, **zero client dependencies, 100% on your hardware**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-Streamable_HTTP%2FSSE-green)](https://modelcontextprotocol.io)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![CI](https://github.com/GermaniU/mineru-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/GermaniU/mineru-mcp/actions/workflows/ci.yml)
[![FastMCP](https://img.shields.io/badge/FastMCP-v2.0+-purple.svg)](https://github.com/jlowin/fastmcp)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**Tags:** `mcp-server` · `mineru` · `pdf-parser` · `ocr` · `latex` · `ai-agents` · `fastmcp` · `claude-code` · `cursor` · `hermes-gateway` · `local-first` · `self-hosted`

---

## 💡 Why It Exists

Extracting structured text, complex tables, and mathematical formulas from PDF documents usually requires heavy Python environments with PyTorch, OCR engines, and computer vision models on every client machine. **MinerU MCP** solves this by acting as a decoupled HTTP/SSE middleware adapter:

- 🚀 **Zero Local Installation**: Any MCP client parses documents over HTTP/SSE on port `8202` by passing a local `file_path` or sending a Base64 encoded payload in `file_base64`.
- 📊 **Structured Markdown & LaTeX**: Converts headers, lists, complex tables, and math equations into standard LaTeX ready for RAG pipelines.
- 🧠 **Flexible Execution (CPU / GPU VRAM)**: Default CPU pipeline without touching VRAM, or optional VLM acceleration coordinated with the GPU Arbiter.

---

## 🏗️ Architecture & Component Boundaries

> ⚠️ **IMPORTANT: System Boundaries**
>
> `mineru-mcp` is **strictly the MCP transport & interface layer**. It does NOT include the `mineru-api` processing engine or HuggingFace cached weights.
> For host server deployment instructions, see [docs/SERVER_SETUP.md](docs/SERVER_SETUP.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

```
 +-------------------------------------------------------+
 |                 MCP Clients (LAN)                     |
 | (Claude Code CLI / Cursor / Windsurf / Hermes Gateway)|
 +-------------------------------------------------------+
                             |
                             | HTTP / SSE (Port 8202)
                             v
 +-------------------------------------------------------+
 |                   mineru-mcp Server                   |
 |        (FastMCP + File Path / Base64 Decoder)         |
 +-------------------------------------------------------+
                             |
                             | Loopback HTTP (Port 8002)
                             v
 +-------------------------------------------------------+
 |                  MinerU Backend Host                  |
 |  (mineru-api + PDF-Extract-Kit + HuggingFace Cache)   |
 +-------------------------------------------------------+
```

---

## 📦 Quickstart

### Prerequisites
- Python 3.11+
- `uv` (recommended) or `pip`

### Install

```bash
git clone https://github.com/GermaniU/mineru-mcp.git
cd mineru-mcp

# Create venv and install
uv venv
source .venv/bin/activate
uv pip install -e .
```

---

## ⚙️ Configuration (Environment Variables)

Create a `.env` file or export environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MINERU_API_URL` | `http://127.0.0.1:8002` | Loopback URL where `mineru-api` engine is listening. |
| `MCP_HOST` | `0.0.0.0` | Host binding for the MCP server. |
| `MCP_PORT` | `8202` | HTTP/SSE port for the MCP server. |
| `UPLOAD_DIR` | `/tmp/mineru_uploads` | Temporary directory for Base64 PDF decoding. |

---

## 🛠️ MCP Tool Reference

### 1. `parse_pdf`
Extracts PDF document content returning structured Markdown, LaTeX formulas, and extracted images.

- **Parameters**:
  - `file_path` (*string*, optional): Absolute path to PDF file on host file system.
  - `file_base64` (*string*, optional): Base64 encoded PDF file content for remote clients.
  - `file_name` (*string*, optional): Original filename when using `file_base64`.
  - `backend` (*string*, optional): Parsing engine backend (`pipeline` for CPU, `hybrid-engine` or `vlm-engine` for GPU). Default: `"pipeline"`.
  - `is_ocr` (*boolean*, optional): Force OCR processing. Default: `false`.
  - `data_id` (*string*, optional): Optional document identifier.

### 2. `get_task_status`
Retrieves extraction processing status for an asynchronous task given its `task_id`.

### 3. `list_tasks`
Lists recent document extraction tasks and their status.

### 4. `mineru_health`
Retrieves backend engine health: `mineru-api` availability and system resource usage.

---

## 🔗 Client Integration Guides

### Claude Code CLI (`~/.claude.json`)

```json
{
  "mcpServers": {
    "mineru": {
      "url": "http://192.168.68.108:8202/mcp"
    }
  }
}
```

### Hermes Gateway (`~/.hermes/config.yaml`)

```yaml
mcp_servers:
  mineru:
    url: "http://192.168.68.108:8202/mcp"
    transport: "http"
```

---

## 🧪 Running Tests

```bash
uv run --with pytest --with pytest-asyncio pytest
```

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
