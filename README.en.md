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
                             | Loopback HTTP (Port 8000)
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

### With Docker (stdio, no clone)

The `ghcr.io/germaniu/mineru-mcp` image speaks MCP over stdio and calls a `mineru-api` running on the host. Add it to your MCP client:

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

Inside the container `file_path` refers to the container's file system: send documents with `file_base64` + `file_name`, or mount a directory with `-v`. There is no systemd in the container, so no wake-on-demand and no GPU Broker: `mineru-api` must already be up.

---

## ⚙️ Configuration (Environment Variables)

Create a `.env` file or export environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MINERU_URL` | `http://127.0.0.1:8000` | URL of `mineru-api`. Only loopback and `host.docker.internal` are accepted; with any other host the tools refuse to send documents. |
| `MINERU_BACKEND` | `pipeline` | Backend when a call leaves it empty (`pipeline`, `hybrid-engine`, `vlm-engine`). |
| `MINERU_PARSE_METHOD` | `auto` | Extraction method when a call leaves it empty (`auto`, `txt`, `ocr`). |
| `MINERU_LANG` | `es` | OCR language when a call leaves it empty. |
| `MCP_HOST` | `0.0.0.0` | Host binding for HTTP mode. |
| `MCP_PORT` | `8202` | Port for HTTP mode. |
| `MCP_AUTH_TOKEN` | *(empty = no auth)* | If set, HTTP mode requires `Authorization: Bearer <token>` on every request. |
| `MCP_TRANSPORT` | *(empty = HTTP)* | `stdio` is the same as passing `--stdio`. |

What each setting protects and what it doesn't: [SECURITY.md](SECURITY.md).

---

## 🛠️ MCP Tool Reference

| Tool | What it does |
|------|--------------|
| `parse_document` | Synchronous parse (30-120 s) of a PDF, DOCX, PPTX, XLSX or image into Markdown. Input: `file_path` (path on the server) or `file_base64` + `file_name`. Optional: `backend`, `effort`, `image_analysis`, `parse_method`, `lang`, `formula_enable`, `table_enable`, `start_page`, `end_page`. |
| `submit_parse_task` | Same as `parse_document` but asynchronous: returns a `task_id`. For documents over ~50 pages. |
| `get_task_status` | Task status (`pending` / `processing` / `completed` / `failed`). |
| `get_task_result` | Markdown of a completed task. |
| `mineru_health` | `mineru-api` availability, version and queued tasks. |

`hybrid-engine` + `effort=high` + `image_analysis=true` turns figures into Mermaid diagrams.

---

## 🧭 How does it compare to other document MCP servers?

There are three families, and they solve different problems.

| | **MinerU MCP** (this) | Official MinerU MCP (cloud) | General converters (Docling, MarkItDown) |
|---|---|---|---|
| Where parsing happens | Your `mineru-api`, on your hardware | MinerU's cloud API | The machine running the MCP |
| Your documents leave your network | **No** (external URLs are blocked) | Yes | No |
| Account / token | None | MinerU API token | None |
| Client dependencies | None (HTTP) or just Docker (stdio) | Python (`uvx mineru-open-mcp`) | The full conversion engine |
| Shares the GPU with a local LLM | **Yes** (GPU Broker) | N/A | No |
| Engine | MinerU (`pipeline` / `vlm` / `hybrid`) | MinerU | Their own |

**In one sentence:**
- No GPU or server, and fine with uploading documents → the official MinerU cloud MCP.
- You want a converter that lives on the same machine as the client → Docling or MarkItDown.
- You already run (or want) MinerU on your own server, **without documents leaving your network**, shared by every client on the LAN → this one.

---

## 🔗 Client Integration Guides

### Claude Code CLI (`~/.claude.json`)

```json
{
  "mcpServers": {
    "mineru": {
      "url": "http://<YOUR_SERVER_IP>:8202/mcp"
    }
  }
}
```

### Hermes Gateway (`~/.hermes/config.yaml`)

```yaml
mcp_servers:
  mineru:
    url: "http://<YOUR_SERVER_IP>:8202/mcp"
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
