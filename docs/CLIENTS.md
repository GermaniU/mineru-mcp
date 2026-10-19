# Conectar tu cliente MCP

El servidor habla dos transportes:

- **Streamable HTTP** (el uso principal) — `mineru-mcp` corre en la máquina de `mineru-api` y los clientes de tu red se conectan a `http://<server>:8202/mcp`. Un solo proceso compartido; los clientes no instalan nada.
- **stdio** — el cliente lanza `mineru-mcp --stdio` como subproceso. Solo tiene sentido si el cliente corre **en la misma máquina** que `mineru-api`, porque `MINERU_URL` tiene que ser loopback (con cualquier otro host las tools se niegan a enviar documentos, ver [`SECURITY.md`](../SECURITY.md)).

En los ejemplos la URL es `http://localhost:8202/mcp`. Si el cliente está en otra máquina, cambia `localhost` por el nombre o la IP del server en tu red.

---

## Modo HTTP

Arranca el server (ver [Quickstart](../README.md#-quickstart)) y apunta tu cliente al endpoint.

### Claude Code

Regístralo con el CLI (scope `user` = disponible en todos tus proyectos):

```bash
claude mcp add -s user -t http mineru http://localhost:8202/mcp
```

Si el server tiene `MCP_AUTH_TOKEN`, pasa el header:

```bash
claude mcp add -s user -t http mineru http://localhost:8202/mcp \
  --header "Authorization: Bearer <tu-token>"
```

> ⚠️ **Las tools aparecen en sesiones NUEVAS**, no en la sesión donde registraste el server. Verifica con `claude mcp list`.

Las tools aparecen como `mcp__mineru__parse_document`, etc.

Ver también: [`examples/claude-code.json`](../examples/claude-code.json) — la entrada que `claude mcp add` deja en `~/.claude.json`.

### Cursor

`Settings → Cursor Settings → MCP Servers → Add new MCP Server`, o en `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "mineru": {
      "url": "http://localhost:8202/mcp"
    }
  }
}
```

Ver también: [`examples/cursor.json`](../examples/cursor.json).

### Continue (VS Code / JetBrains)

En `~/.continue/config.json`:

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "transport": {
          "type": "streamable-http",
          "url": "http://localhost:8202/mcp"
        }
      }
    ]
  }
}
```

Ver también: [`examples/continue.json`](../examples/continue.json).

### OpenCode

En `~/.config/opencode/config.json`:

```json
{
  "mcp": {
    "mineru": {
      "type": "remote",
      "url": "http://localhost:8202/mcp",
      "enabled": true
    }
  }
}
```

Ver también: [`examples/opencode.json`](../examples/opencode.json).

### Hermes Gateway

En `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  mineru:
    url: "http://localhost:8202/mcp"
    transport: "http"
```

Ver también: [`examples/hermes.yaml`](../examples/hermes.yaml).

### Windsurf y cualquier otro cliente

Añade un servidor MCP de tipo **Streamable HTTP** (algunos clientes lo llaman *SSE / HTTP*) con la URL `http://localhost:8202/mcp`.

---

## Modo stdio (misma máquina que `mineru-api`)

### Con `uvx`

Necesitas [`uv`](https://docs.astral.sh/uv/getting-started/installation/). `uvx` descarga el server desde GitHub la primera vez, lo cachea y lo lanza en cada sesión:

```
uvx --from git+https://github.com/GermaniU/mineru-mcp mineru-mcp --stdio
```

Para Claude Desktop (`Settings → Developer → Edit Config` abre `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mineru": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/GermaniU/mineru-mcp",
        "mineru-mcp",
        "--stdio"
      ],
      "env": {
        "MINERU_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

Si no aparece, suele ser el `PATH`: las apps de escritorio no leen el de tu shell, así que pon la ruta absoluta de `uvx` en `command` (la que devuelve `which uvx`).

Ver también: [`examples/claude-desktop.json`](../examples/claude-desktop.json).

### Con Docker

La imagen `ghcr.io/germaniu/mineru-mcp` habla stdio y llega al `mineru-api` del host por `host.docker.internal`. La config está en el [README](../README.md#opción-b--stdio-con-docker). Dentro del contenedor `file_path` es una ruta del contenedor: manda los documentos con `file_base64` + `file_name`, o monta un directorio con `-v`.
