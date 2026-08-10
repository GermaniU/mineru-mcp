# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
