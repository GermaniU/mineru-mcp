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

<p align="center">
  <img src="docs/assets/demo.gif" alt="The agent sends two pages of a real paper over MCP and gets back Markdown with a LaTeX equation and a table" width="780">
</p>

<p align="center"><sub>The agent sends a PDF over MCP and gets back Markdown with LaTeX equations and tables — MinerU runs on your server, the client never installs PyTorch. Recorded with <a href="scripts/demo_parse.py"><code>scripts/demo_parse.py</code></a> against a real <code>mineru-api</code>. The demo output is in Spanish.</sub></p>

---

## 💡 Why It Exists

Extracting structured text, complex tables, and mathematical formulas from PDF documents usually requires heavy Python environments with PyTorch, OCR engines, and computer vision models on every client machine. **MinerU MCP** solves this by acting as a decoupled HTTP/SSE middleware adapter:

- 🚀 **Zero Local Installation**: Any MCP client parses documents over HTTP/SSE on port `8202` by passing a local `file_path` or sending a Base64 encoded payload in `file_base64`.
- 📊 **Structured Markdown & LaTeX**: Converts headers, lists, complex tables, and math equations into standard LaTeX ready for RAG pipelines.
- 🧠 **The GPU is shared, not fought over**: `pipeline` (default) asks for ~1.5 GB of VRAM; `hybrid-engine` and `vlm-engine` ~4 GB and are more accurate. If the host runs the GPU Broker, every parse requests the VRAM first and hands it back when done, so it coexists with a local LLM on the same card.

---

## ⚡ Quickstart

`mineru-mcp` is only the MCP layer: you need a running `mineru-api` (`mineru==3.4.4`). How to set it up on the host: [`docs/SERVER_SETUP.md`](docs/SERVER_SETUP.md).

There are two ways to run it. Pick one:

| Mode | When | How it starts |
|------|------|---------------|
| **HTTP** | One server on the `mineru-api` machine, shared by every client on your network (the main use case) | You (or a service) start it and it listens on `http://<server>:8202/mcp`. |
| **stdio** | The client runs on the same machine as `mineru-api` | The client launches the process itself (`uvx` or Docker). No open port. |

> Requirement: `uv` ≥ 0.13.4 (or `pip` ≥ 26.2.2); older releases still trust the compromised emSign CA (GHSA-6q48-6c7w-9gw2). `uv pip install -e .` enforces it (`[tool.uv] required-version` in `pyproject.toml`); `uvx --from git+…` does not, because it runs outside the project: check `uv --version`.

### Option A — HTTP (shared server)

```bash
git clone https://github.com/GermaniU/mineru-mcp.git
cd mineru-mcp
uv venv && source .venv/bin/activate
uv pip install -e .
MINERU_URL=http://127.0.0.1:8000 mineru-mcp
```

MCP endpoint: `http://<server>:8202/mcp`. Paste it into your client config (see [`docs/CLIENTS.md`](docs/CLIENTS.md) — Claude Code, Cursor, Continue, OpenCode, Hermes Gateway; written in Spanish, the snippets are universal).

### Option B — stdio with Docker

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

> Without Docker: `uvx --from git+https://github.com/GermaniU/mineru-mcp mineru-mcp --stdio`, with `uv` ≥ 0.13.4 (config in [`docs/CLIENTS.md`](docs/CLIENTS.md#con-uvx)).

### 🔍 Diagnostics

`mineru_health` reports whether `mineru-api` answers, its version and queued tasks, and tells a **sleeping** backend (stopped for inactivity) apart from a **broken** one. You can call it without an MCP client using the [curl smoke test](#-smoke-test-with-curl).

---

## ⚙️ Configuration (Environment Variables)

Create a `.env` file or export environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MINERU_URL` | `http://127.0.0.1:8000` | URL of `mineru-api`. Only loopback and `host.docker.internal` are accepted; with any other host the tools refuse to send documents. |
| `MINERU_BACKEND` | `pipeline` | Backend when a call leaves it empty (`pipeline`, `hybrid-engine`, `vlm-engine`). |
| `MINERU_PARSE_METHOD` | `auto` | Extraction method when a call leaves it empty (`auto`, `txt`, `ocr`). |
| `MINERU_LANG` | `es` | OCR language when a call leaves it empty. |
| `MINERU_SYSTEMCTL_SCOPE` | `user` | Where the `mineru-api` unit lives, used to wake it and check its state: `user` (`systemctl --user`) or `system` (`/etc/systemd/system`). Any other value stops the server from starting. |
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

`start_page` and `end_page` are 0-based: the demo asks for `start_page: 4, end_page: 5` and gets pages 5 and 6 of the paper. `hybrid-engine` + `effort=high` + `image_analysis=true` turns figures into Mermaid diagrams.

---

## 🎯 Current Scope

MinerU MCP is deliberately thin. It does **one thing**: carry documents from an MCP client to your `mineru-api` and return the Markdown. MinerU does the parsing.

### What it DOES
- ✅ PDF, DOCX, PPTX, XLSX, PNG and JPG to Markdown with headings, tables (HTML) and formulas (LaTeX).
- ✅ Takes the document as a server path (`file_path`) or as content (`file_base64` + `file_name`) from another machine.
- ✅ Synchronous parsing for short documents and asynchronous with a `task_id` for long ones, with page ranges.
- ✅ If `mineru-api` is stopped and systemd is available, starts it (`systemctl --user start`, or without `--user` with `MINERU_SYSTEMCTL_SCOPE=system`) and waits for it to answer before parsing.
- ✅ Requests and releases VRAM through the GPU Broker when the host has one.

### What it does NOT do (yet)
- ❌ **It does not ship `mineru-api` or the models.** They are installed separately on the host, with their services: [`docs/SERVER_SETUP.md`](docs/SERVER_SETUP.md).
- ❌ **It does not send documents outside your network.** If `MINERU_URL` is not loopback it refuses to send them; it does not use MinerU's cloud API.
- ❌ **It does not return the extracted images**, only the Markdown.
- ❌ **No partial streaming** of the Markdown on long extractions: use `submit_parse_task` and poll the status.
- ❌ **It does not store documents or results.** The temporary file for a base64 payload is deleted when the parse ends.
- ❌ **In Docker there is no wake-on-demand and no GPU Broker:** `mineru-api` must be up.

If you need something from the NOT list, open an [issue](https://github.com/GermaniU/mineru-mcp/issues) with a real use case.

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

## 🔌 Connect your client

Copy-paste configuration in [`docs/CLIENTS.md`](docs/CLIENTS.md) (HTTP and stdio):

- 🟦 **Claude Code** — `claude mcp add -s user -t http mineru http://<server>:8202/mcp` (tools show up in new sessions).
- 🟧 **Cursor** — Settings → MCP Servers → Add new MCP Server.
- 🟩 **Continue** (VS Code / JetBrains) — `~/.continue/config.json`.
- 🟪 **OpenCode** — `~/.config/opencode/config.json`.
- 🟨 **Hermes Gateway** — `mcp_servers` in `~/.hermes/config.yaml`.
- 🟫 **Claude Desktop** — stdio with `uvx` or Docker, on the `mineru-api` machine.

Ready-made snippets in [`examples/`](examples/).

---

## 🧪 Smoke test with curl

HTTP mode is *stateless*: a single request is enough, no `initialize` and no `mcp-session-id`.

```bash
curl -sS -X POST http://localhost:8202/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"mineru_health","arguments":{}}}'
```

With `MCP_AUTH_TOKEN`, add `-H "Authorization: Bearer <token>"`.

For the full check (health + a real parse of two pages of an arXiv paper), run the GIF demo:

```bash
MCP_DEMO_URL=http://localhost:8202/mcp python scripts/demo_parse.py
```

---

## 🧱 Architecture

> ⚠️ **System boundaries:** `mineru-mcp` is **strictly the MCP transport & interface layer**. It does NOT include the `mineru-api` processing engine or HuggingFace cached weights.

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

Each tool lives in `src/mineru_mcp/tools/`; `server.py` only registers them with FastMCP and starts the transport. Technical details in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## 🤝 Contributing

PRs, issues and forks welcome (MIT).

**Rules (summary):**
1. **Small, direct changes.** Touch the narrowest code path that explains the problem.
2. **No speculative abstractions** and no new dependencies unless needed.
3. **Tool names and parameters are preserved:** clients depend on them.
4. **Identifiers in English**, comments and commits in Spanish. Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`).

Full details in [`CONTRIBUTING.md`](CONTRIBUTING.md).

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest          # unit tests, no mineru-api needed
ruff check .
```

---

## 🩹 Troubleshooting

The tools answer in Spanish; the messages below are quoted as they appear.

**`mineru_health` returns `MinerU no disponible (el backend está inactivo)`**
- `mineru-api` is stopped (for example by an idle watchdog that hands VRAM back). Not an error: `parse_document` or `submit_parse_task` start it.

**`BLOQUEADO por seguridad: MINERU_URL apunta a …`**
- `MINERU_URL` is neither loopback nor `host.docker.internal`. On purpose: documents do not leave your machine. See [`SECURITY.md`](SECURITY.md).

**`MinerU no responde en … y aquí no hay systemd para arrancarlo`**
- You are on Docker or macOS: there is no way to wake `mineru-api`. Start it by hand and retry.

**`406 Not Acceptable` when you `curl` the endpoint**
- The `Accept: application/json, text/event-stream` header is missing.

**`401 {"error":"unauthorized"}`**
- The server has `MCP_AUTH_TOKEN`: send `Authorization: Bearer <token>`.

**`Error: timeout. El documento puede ser muy grande`**
- Use `submit_parse_task` and poll `get_task_status`, or parse in ranges with `start_page` / `end_page`.

---

## 📚 Documentation

- [`docs/SERVER_SETUP.md`](docs/SERVER_SETUP.md) — installing `mineru-api`, models and services on the host.
- [`docs/CLIENTS.md`](docs/CLIENTS.md) — config for Claude Code, Cursor, Continue, OpenCode, Hermes Gateway and Claude Desktop.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components, request flow and GPU Arbiter.
- [`SECURITY.md`](SECURITY.md) — threat model and how to report vulnerabilities.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — dev environment, style rules and workflow.
- [`CHANGELOG.md`](CHANGELOG.md) — change history.

---

## 📄 License

[MIT](LICENSE) — use it, fork it, improve it.

---

**Made by [@GermaniU](https://github.com/GermaniU).** If it helped you, a ⭐ helps more people find it. If something broke, open an issue and we'll fix it.
