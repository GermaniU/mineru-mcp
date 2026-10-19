---
name: Bug report
about: Something is broken or behaving unexpectedly
title: "fix: <short description>"
labels: bug
assignees: ""
---

<!-- Security problem? Do NOT open a public issue. See SECURITY.md. -->

## Version

<!-- Output of: pip show mineru-mcp | grep Version  OR  the Docker image tag you're using -->

## Installation mode

<!-- Check one -->
- [ ] HTTP server (`mineru-mcp`, by hand or as a service)
- [ ] stdio with `uvx`
- [ ] Docker image (`ghcr.io/germaniu/mineru-mcp`)
- [ ] Other (describe below)

## Environment

- OS:
- Python version (`python --version`):
- MinerU version (from `mineru_health`):
- Backend (`pipeline`, `hybrid-engine`, `vlm-engine`):
- MCP client (Claude Code, Cursor, Hermes Gateway, …):

## Configuration

<!-- Any variables you changed from .env.example. Never paste MCP_AUTH_TOKEN. -->

```
MINERU_URL=
MINERU_BACKEND=
MCP_HOST=
MCP_PORT=
```

## Steps to reproduce

1.
2.
3.

<!-- If you can, link a public document that reproduces it. Do not attach private documents. -->

## Expected behavior

<!-- What should have happened -->

## Actual behavior

<!-- What actually happened — include the full message returned by the tool -->

## Diagnostics

```
curl -sS -X POST http://localhost:8202/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"mineru_health","arguments":{}}}'
```

<!-- Paste the output here -->

## Additional context

<!-- Logs, screenshots, relevant environment details -->

---

> Issues in Spanish are welcome too. / Los issues en español también son bienvenidos.
