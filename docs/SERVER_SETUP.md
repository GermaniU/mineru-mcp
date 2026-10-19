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

Por defecto el MCP maneja `mineru-api` como **unit de usuario** (`systemctl --user`): el wake-on-demand la arranca y `mineru_health` consulta su estado sin sudo ni polkit. Para eso las dos units tienen que vivir en la sesión systemd del mismo usuario. Si prefieres units de sistema, ve a [Modo system](#modo-system-mineru_systemctl_scopesystem).

### 1. Service MinerU API Backend (`~/.config/systemd/user/mineru-api.service`)

```ini
[Unit]
Description=MinerU PDF Parsing API Engine
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/stack/mineru-api
Environment="PATH=%h/stack/mineru-api/.venv/bin:/usr/bin"
ExecStart=%h/stack/mineru-api/.venv/bin/mineru-api --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

No hace falta habilitarla: el MCP la arranca cuando llega un documento y un idle-watchdog puede apagarla para devolver la VRAM.

### 2. Service MinerU MCP Server (`~/.config/systemd/user/mineru-mcp.service`)

```ini
[Unit]
Description=MinerU MCP Server (FastMCP HTTP)
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/Sites/mineru-mcp
Environment="MINERU_URL=http://127.0.0.1:8000"
Environment="MCP_PORT=8202"
Environment="MCP_HOST=0.0.0.0"
ExecStart=%h/Sites/mineru-mcp/.venv/bin/mineru-mcp
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now mineru-mcp.service
# Sin linger, las units de usuario mueren al cerrar sesión y no arrancan al boot:
sudo loginctl enable-linger "$USER"
```

### Modo system (`MINERU_SYSTEMCTL_SCOPE=system`)

Si `mineru-api` es unit de sistema (`/etc/systemd/system/mineru-api.service`, con `User=<YOUR_USER>` y `WantedBy=multi-user.target`), agrega `Environment="MINERU_SYSTEMCTL_SCOPE=system"` al service del MCP. El MCP llama `systemctl start` / `is-active` **sin sudo**, así que el usuario del MCP necesita permiso de polkit para manejar esa unit:

```js
// /etc/polkit-1/rules.d/50-mineru-api.rules
polkit.addRule(function (action, subject) {
  if (action.id == "org.freedesktop.systemd1.manage-units" &&
      action.lookup("unit") == "mineru-api.service" &&
      subject.user == "<YOUR_USER>") {
    return polkit.Result.YES;
  }
});
```

No dejes la misma unit instalada en los dos scopes: el MCP solo mira el que configuraste y el otro puede quedarse con el puerto. Cualquier valor distinto de `user` o `system` hace que el MCP no arranque.

---

## ⚡ Step 3: GPU Broker (opcional)

Si el host tiene el GPU Broker (`~/stack/gpu-broker/gpu-broker.sh`), cada parseo le pide la VRAM antes y la devuelve al terminar: ~1.5 GB para `pipeline` y ~4 GB para `hybrid-engine` / `vlm-engine`.

Sin broker, el fallback detiene `comfyui.service` si está activo. Esa unit es de sistema, así que el fallback usa `systemctl` sin `--user` sin importar `MINERU_SYSTEMCTL_SCOPE`, y el usuario del MCP necesita el mismo tipo de regla de polkit para `comfyui.service`.

---

## 🌐 Step 4: Firewall (UFW)

Para permitir que otros nodos de la red LAN consuman el MCP en el puerto `8202`:

```bash
sudo ufw allow from <YOUR_LAN_CIDR> to any port 8202 proto tcp comment "MinerU MCP HTTP"
sudo ufw reload
```
