FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Dentro del contenedor 127.0.0.1 es el propio contenedor: mineru-api vive
    # en el host. server.json pasa --add-host host.docker.internal:host-gateway
    # para que este nombre resuelva también en Linux.
    MINERU_URL=http://host.docker.internal:8000 \
    # Dentro del contenedor hay que escuchar en todas las interfaces para que
    # el port mapping funcione; publica el puerto solo en 127.0.0.1 del host.
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8202

# El MCP Registry verifica la propiedad de la imagen con este label: su valor
# debe coincidir EXACTO con el "name" de server.json.
LABEL io.modelcontextprotocol.server.name="io.github.GermaniU/mineru-mcp"

WORKDIR /app

# README.md hace falta: pyproject.toml lo declara como readme del paquete.
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir . \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin mcp

# Los PDFs en base64 se decodifican en /tmp; no hace falta escribir en otro lado.
USER mcp

EXPOSE 8202

# Sin argumentos arranca en HTTP; el cliente MCP pasa --stdio para el modo stdio.
ENTRYPOINT ["mineru-mcp"]
