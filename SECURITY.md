# Seguridad

Este documento explica qué protege `mineru-mcp`, qué **no** protege y cómo reportar una vulnerabilidad.

*English summary: report vulnerabilities privately via the repository's **Security → Report a vulnerability** tab. Do not open public issues for security problems.*

---

## Modelo de amenazas

`mineru-mcp` es un cliente delgado: recibe un documento por MCP (ruta local o contenido en base64), lo envía a un `mineru-api` **que corre en tu propia máquina** y devuelve el Markdown. No guarda los documentos ni los resultados.

### Lo que protege

| Riesgo | Cómo se mitiga |
|---|---|
| Tus documentos terminan en un servidor de terceros | Si `MINERU_URL` no apunta a loopback (`localhost`, `127.0.0.1`, `0.0.0.0`) o a `host.docker.internal`, las tools de parseo **se niegan a enviar** el archivo. |
| Otro equipo de la red usa el server en modo HTTP | `MCP_AUTH_TOKEN` opcional: si está definido, cada request HTTP debe traer `Authorization: Bearer <token>`. |
| Formatos inesperados | Solo se aceptan `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.png`, `.jpg` y `.jpeg`. |
| El contenedor compromete el host | La imagen Docker corre como usuario sin privilegios (`uid 10001`) y no monta nada del host. |

### Lo que NO protege

- **El modo HTTP sin token.** Por defecto escucha en `0.0.0.0:8202` y sin `MCP_AUTH_TOKEN` cualquiera que llegue al puerto puede parsear documentos y, con `file_path`, **leer cualquier archivo soportado al que tenga acceso el usuario del proceso**. Úsalo solo en una red de confianza, define el token, o cambia `MCP_HOST` a `127.0.0.1`.
- **`file_path` es una ruta del servidor**, no del cliente. Quien puede llamar a la tool puede pedir cualquier ruta legible por el proceso. En Docker eso se limita al sistema de archivos del contenedor.
- **CORS abierto en modo HTTP** (`allow_origins=["*"]`). Si lo expones sin token, una página web que visites podría llamarlo desde tu navegador. Con `MCP_AUTH_TOKEN` el navegador no tiene el token y la llamada falla.
- **La comprobación de `MINERU_URL` es por prefijo de la URL**, no resuelve DNS. Protege contra un error de configuración, no contra alguien que ya controla tus variables de entorno.
- **El tráfico a `mineru-api` va en HTTP plano.** Está pensado para loopback; no lo pongas en otra máquina sin un túnel.
- **El contenido del documento.** El Markdown que devuelve MinerU puede contener instrucciones dirigidas al agente (prompt injection). Trátalo como entrada no confiable.

---

## Configuración recomendada

| Ajuste | Recomendación |
|---|---|
| Transporte | stdio (`--stdio`) si el cliente corre en la misma máquina. HTTP solo si varios clientes de tu red lo comparten. |
| `MCP_AUTH_TOKEN` | Defínelo siempre que uses HTTP fuera de loopback. |
| `MCP_HOST` | `127.0.0.1` si no necesitas acceso desde la red. En Docker usa `-p 127.0.0.1:8202:8202`. |
| `MINERU_URL` | Loopback (`http://127.0.0.1:8000`) o, en Docker, `http://host.docker.internal:8000`. |

---

## Reportar una vulnerabilidad

**No abras un issue público.** Usa el reporte privado de GitHub: ve a la pestaña **Security** del repositorio, elige **Report a vulnerability** e incluye:

- los pasos para reproducirlo;
- el impacto (qué datos se exponen o qué puede hacer un atacante);
- la versión o el commit afectado.

Puedes escribir en español o en inglés.
