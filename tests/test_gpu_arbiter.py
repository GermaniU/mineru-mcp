"""Tests del fallback del GPU arbiter cuando no hay broker."""

from mineru_mcp import gpu_arbiter


def test_sin_broker_ni_systemd_no_toca_nada(monkeypatch):
    """En un contenedor no hay broker ni systemctl: se parsea sin coordinar GPU."""
    monkeypatch.setattr(gpu_arbiter, "GPU_BROKER", "/no/existe/gpu-broker.sh")
    monkeypatch.setattr(gpu_arbiter.shutil, "which", lambda _: None)

    def _no_debe_correr(*args, **kwargs):
        raise AssertionError(f"subprocess.run no debía llamarse: {args}")

    monkeypatch.setattr(gpu_arbiter.subprocess, "run", _no_debe_correr)

    assert gpu_arbiter.ensure_gpu_for_mineru("pipeline") == (None, None)
