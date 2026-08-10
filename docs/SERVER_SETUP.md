# Guía de Instalación del Servidor Backend (MinerU API & GPU Arbiter)

> ⚠️ **Nota de Separación de Componentes**: Este repositorio (`mineru-mcp`) contiene **únicamente el adaptador MCP**. Para que el sistema funcione, debes tener desplegado el servidor backend de `mineru-api`, los modelos de HuggingFace descargados en caché y los servicios systemd en la máquina host.

---

## 📋 Requisitos del Servidor Host

- **Sistema Operativo**: Linux (Pop!_OS 22.04 LTS / Ubuntu 22.04 LTS recomendado)
- **CPU / GPU**: CPU multi-núcleo para backend `pipeline`. Opcional: NVIDIA GPU (>= 6GB VRAM) para backend `hybrid-engine` / `vlm-engine`.
- **Python**: Python 3.11 / 3.12 con soporte `uv` o `venv`.
- **Librería Backend**: `mineru==3.4.4` (provee el comando ejecutable `mineru-api`).

---

## 🛠️ Step 1: Instalación de MinerU Engine

1. **Crear Entorno Virtual**:
   ```bash
   mkdir -p ~/stack/mineru-api
   cd ~/stack/mineru-api
   uv venv --python 3.12
   source .venv/bin/activate
   ```

2. **Instalar `mineru` con Dependencias CUDA/CPU**:
   ```bash
   uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
   uv pip install mineru==3.4.4
   ```

3. **Descargar Modelos HuggingFace en Cache (`~/.cache/huggingface`)**:
   - `PDF-Extract-Kit` (Detección de layouts, fórmulas y tablas)
   - `MinerU2.5-VLM` (Opcional para reconocedores basados en visión)

---

## ⚡ Step 2: Systemd Services

### 1. Service MinerU API Backend (`/etc/systemd/system/mineru-api.service`)

```ini
[Unit]
Description=MinerU PDF Parsing API Engine
After=network.target

[Service]
Type=simple
User=<YOUR_USER>
WorkingDirectory=<HOME>/stack/mineru-api
Environment="PATH=<HOME>/stack/mineru-api/.venv/bin:/usr/bin"
ExecStart=<HOME>/stack/mineru-api/.venv/bin/mineru-api --host 127.0.0.1 --port 8002
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 2. Service MinerU MCP Server (`/etc/systemd/system/mineru-mcp.service`)

```ini
[Unit]
Description=MinerU MCP Server (FastMCP HTTP)
After=network.target mineru-api.service

[Service]
Type=simple
User=<YOUR_USER>
WorkingDirectory=<HOME>/Sites/mineru-mcp
Environment="PATH=<HOME>/Sites/mineru-mcp/.venv/bin:/usr/bin"
Environment="MINERU_API_URL=http://127.0.0.1:8002"
Environment="MCP_PORT=8202"
Environment="MCP_HOST=0.0.0.0"
ExecStart=<HOME>/Sites/mineru-mcp/.venv/bin/python -m mineru_mcp.server
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

---

## ⚡ Step 3: Configuración del GPU Broker & Arbiter (Opcional VLM)

Si se utiliza el backend `hybrid-engine` o `vlm-engine` que consume VRAM (~4GB), la máquina host debe contar con la regla de sudoers para conmutación de servicios:

```ini
# /etc/sudoers.d/gpu-arbiter
# Permisos limitados para el arbitraje de GPU
<YOUR_USER> ALL=(ALL) NOPASSWD: /usr/bin/systemctl start mineru-api.service
<YOUR_USER> ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop mineru-api.service
<YOUR_USER> ALL=(ALL) NOPASSWD: /usr/bin/systemctl is-active mineru-api.service
```

> **Importante**: El archivo `/etc/sudoers.d/gpu-arbiter` debe tener permisos `0440` (`sudo chmod 0440 /etc/sudoers.d/gpu-arbiter`).

---

## 🌐 Step 4: Firewall (UFW)

Para permitir que otros nodos de la red LAN consuman el MCP en el puerto `8202`:

```bash
sudo ufw allow from <YOUR_LAN_CIDR> to any port 8202 proto tcp comment "MinerU MCP HTTP"
sudo ufw reload
```
