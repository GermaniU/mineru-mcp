# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Sin publicar]

### Añadido
- **Registro en el MCP Registry**: `server.json` (namespace `io.github.GermaniU/mineru-mcp`, imagen OCI de GHCR por stdio), `Dockerfile` con el label `io.modelcontextprotocol.server.name` y job `mcp-registry` en `release.yml` (login OIDC, sin secretos). El job `docker` de CI construye la imagen, comprueba que el label coincida con `server.json` y hace un smoke test stdio del contenedor.
- `SECURITY.md`: modelo de amenazas (qué protege y qué no) y cómo reportar vulnerabilidades en privado.
- README (ES/EN): instalación con Docker y sección **«¿Y los otros servidores MCP para documentos?»**.

### Corregido
- Sin systemd (contenedor Docker, macOS) las tools ya no revientan con `FileNotFoundError`: el wake-on-demand devuelve un error claro en vez de esperar 90 s, `mineru_health` reporta la URL inalcanzable y el fallback del GPU arbiter no intenta parar ComfyUI.
- README y `.env.example` documentaban variables que el código no lee (`MINERU_API_URL`, `UPLOAD_DIR`) y tools que ya no existen (`parse_pdf`, `list_tasks`).

## [0.1.0] - 2026-08-09

### Añadido
- **Transporte HTTP/SSE**: Migración de MCP de stdio a servidor FastMCP HTTP/SSE accesible en puerto `8202`.
- **Soporte Híbrido de Documentos**:
  - `file_path`: Procesamiento directo para archivos locales en la máquina host.
  - `file_base64`: Decodificación asíncrona para clientes remotos enviando PDFs en Base64.
- **Integración GPU Arbiter**: Coordinación VRAM para backends de inferencia por visión (`vlm-engine` / `hybrid-engine`).
- **Herramientas MCP**:
  - `parse_pdf`: Extracción de Markdown, código LaTeX de ecuaciones, tablas e imágenes.
  - `get_task_status`: Monitoreo de tareas asíncronas pesadas.
  - `list_tasks`: Histórico de procesamiento de documentos.
  - `mineru_health`: Monitor de salud del backend `mineru-api`.
- **Documentación Profesional**: Cobertura de arquitectura (`docs/ARCHITECTURE.md`), instalación del servidor backend (`docs/SERVER_SETUP.md`), guías de contribución y configuración multi-cliente.
