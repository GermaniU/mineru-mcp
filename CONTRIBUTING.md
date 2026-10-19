# Guía de Contribución a `mineru-mcp`

¡Gracias por tu interés en contribuir a `mineru-mcp`! Este proyecto sigue estándares de clean code, vertical slices y verificabilidad continua.

---

## 🛠️ Entorno de Desarrollo Local

### Requisitos Previos
- Python 3.11+
- `uv` o `venv`
- Instancia activa de `mineru-api` (opcional para tests mockeados, requerida para integración)

### Setup

```bash
# Clonar repositorio
git clone https://github.com/GermaniU/mineru-mcp.git
cd mineru-mcp

# Crear entorno virtual e instalar dependencias con dev extras
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

---

## 🧪 Ejecución de Pruebas

Los tests están modularizados bajo la carpeta `tests/` y usan `pytest` y `pytest-asyncio`.

```bash
# Ejecutar suite completa
uv run --with pytest --with pytest-asyncio pytest

# Ejecutar test específico
uv run --with pytest --with pytest-asyncio pytest tests/test_helpers.py

# Lint (lo mismo que corre la CI, incluye scripts/)
uv run ruff check .
```

### Demo contra un `mineru-api` real

Los tests usan mocks. Para probar el camino completo (MCP → `mineru-api` → Markdown), levanta el server en un puerto libre apuntando a tu `mineru-api` y corre la demo:

```bash
MINERU_URL=http://127.0.0.1:8000 MCP_HOST=127.0.0.1 MCP_PORT=8299 mineru-mcp
MCP_DEMO_URL=http://127.0.0.1:8299/mcp python scripts/demo_parse.py
```

Es la fuente de `docs/assets/demo.gif`. Para regrabarlo: `asciinema rec --idle-time-limit 2` con la terminal en 92×22 y `agg --font-size 16`.

---

## 📐 Reglas de Estilo y Código

- **Cambios Angostos**: Realiza cambios pequeños y enfocados. Modifica el camino de código más estrecho que solucione el problema.
- **Sin Abstracciones Innecesarias**: Prioriza soluciones prácticas sobre arquitecturas complejas. Las abstracciones solo se justifican cuando eliminan duplicación real de lógica.
- **Cero Código Obsoleto**: Elimina ramas muertas o funciones sin uso de forma agresiva.
- **Estilo Hand-Written**: El código debe leerse limpio y escrito por un humano. Se rechazarán rewrites genéricos con comentarios boilerplate o comprobaciones defensivas sin punto de falla real.

---

## 🔀 Flujo de Trabajo Git

1. Crea una rama desde `master`:
   ```bash
   git checkout master
   git pull
   git checkout -b feature/nombre-descriptivo
   ```
2. Realiza tus cambios manteniendo los tests pasando.
3. Escribe commits descriptivos siguiendo la convención de Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).
4. Abre un Pull Request con la plantilla del repo (`¿Qué cambia y por qué?` / `¿Cómo lo probaste?`).

¿Un bug o una idea? Usa las plantillas de issue. Los problemas de seguridad van por reporte privado: ver [`SECURITY.md`](SECURITY.md).
