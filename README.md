# mineru-mcp

Servidor MCP (Model Context Protocol) que conecta Claude —o cualquier cliente MCP— con [MinerU](https://github.com/opendatalab/MinerU) para parsear documentos **100% en local**: PDF, DOCX, PPTX, XLSX e imágenes → Markdown estructurado (títulos jerárquicos, tablas, fórmulas LaTeX y figuras descritas por VLM).

## Arquitectura

```
Claude (Windows) ──stdio──> mineru_mcp.py (Python, venv en WSL) ──HTTP──> mineru-api :8000 (WSL, systemd)
```

- El MCP es un solo archivo (`mineru_mcp.py`) sobre `mcp` + `httpx`.
- MinerU corre como servicio systemd en WSL; modelos locales en `~/.cache/huggingface` (PDF-Extract-Kit + MinerU2.5 VLM 1.2B).
- Guardia de seguridad: si `MINERU_URL` no es localhost/interna, el MCP **bloquea el envío** de documentos.

## Tools expuestas

| Tool | Uso |
|---|---|
| `parse_document` | Síncrono (~30-120s). Docs cortos. |
| `submit_parse_task` | Asíncrono, devuelve `task_id`. Docs grandes (>50 págs). |
| `get_task_status` / `get_task_result` | Monitoreo y resultado de tareas asíncronas. |
| `mineru_health` | Verifica servidor y métricas. |

## Backends y calidad

| Backend | Cuándo | Notas |
|---|---|---|
| `pipeline` | Default, rápido, sin GPU | Tablas con celdas estilizadas salen con ruido OCR |
| `vlm-engine` | Máxima precisión por página | ~4GB VRAM |
| `hybrid-engine` | **Mejor balance**: pipeline para texto + VLM en bloques difíciles | Con `effort=high` + `image_analysis=true` las figuras salen como **diagramas Mermaid** |

### Gotchas aprendidas (a la mala)

1. **`effort=medium` fuerza `image_analysis=off`** — está en `hybrid_analyze.py` de MinerU, no documentado. Para describir figuras: `hybrid-engine` + `effort=high` + `image_analysis=true`.
2. **systemd**: `mineru-api` crea `output/` relativo al cwd → sin `WorkingDirectory=` en la unit da `PermissionError` (HTTP 500).
3. `nohup ... &` vía `wsl -e` muere al salir wsl.exe — para daemons en WSL, siempre systemd.
4. Celdas de tabla con badges de color quedan vacías incluso en `effort=high` (limitación de MinerU 3.4.0).

## Resultados reales (RTX 3060 12GB)

- NIST AI RMF (48 págs, `pipeline`): ~30s.
- Libro técnico de 157 págs (`hybrid-engine` + `effort=high` + `image_analysis`): **68 min** — 130 figuras, 111 descritas por el VLM, 90 convertidas a Mermaid, 151 bloques de código extraídos.

## Instalación

```bash
# En WSL
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # instala mineru[api] + mcp + httpx

# Servicio systemd: /etc/systemd/system/mineru-api.service
[Unit]
Description=MinerU API server (PDF/document parsing)
After=network.target
[Service]
User=<usuario>
WorkingDirectory=/ruta/al/repo          # ¡obligatorio! (gotcha #2)
ExecStart=/ruta/al/repo/.venv/bin/mineru-api --host 127.0.0.1 --port 8000
Restart=on-failure
[Install]
WantedBy=multi-user.target
```

Registro del MCP en Claude Code (`.claude.json`), desde Windows hacia WSL:

```json
"mineru": {
  "type": "stdio",
  "command": "wsl.exe",
  "args": ["-e", "/mnt/c/Sites/mineru-mcp/.venv/bin/python", "/mnt/c/Sites/mineru-mcp/mineru_mcp.py"],
  "env": { "MINERU_URL": "http://localhost:8000", "MINERU_BACKEND": "pipeline", "MINERU_LANG": "es" }
}
```

Variables de entorno: ver `.env.example`.
