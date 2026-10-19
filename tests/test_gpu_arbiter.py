"""Tests del fallback del GPU arbiter cuando no hay broker."""

import subprocess

from mineru_mcp import gpu_arbiter


def test_sin_broker_ni_systemd_no_toca_nada(monkeypatch):
    """En un contenedor no hay broker ni systemctl: se parsea sin coordinar GPU."""
    monkeypatch.setattr(gpu_arbiter, "GPU_BROKER", "/no/existe/gpu-broker.sh")
    monkeypatch.setattr(gpu_arbiter.shutil, "which", lambda _: None)

    def _no_debe_correr(*args, **kwargs):
        raise AssertionError(f"subprocess.run no debía llamarse: {args}")

    monkeypatch.setattr(gpu_arbiter.subprocess, "run", _no_debe_correr)

    assert gpu_arbiter.ensure_gpu_for_mineru("pipeline") == (None, None)


def test_sin_broker_para_comfyui_como_unit_de_sistema(monkeypatch):
    """comfyui.service es unit de sistema: el fallback no le agrega --user."""
    monkeypatch.setattr(gpu_arbiter, "GPU_BROKER", "/no/existe/gpu-broker.sh")
    monkeypatch.setattr(gpu_arbiter.shutil, "which", lambda _: "/usr/bin/systemctl")
    calls = []

    def _run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="active\n", stderr="")

    monkeypatch.setattr(gpu_arbiter.subprocess, "run", _run)

    assert gpu_arbiter.ensure_gpu_for_mineru("pipeline") == (None, None)
    assert calls == [
        ["systemctl", "is-active", "comfyui.service"],
        ["systemctl", "stop", "comfyui.service"],
    ]
