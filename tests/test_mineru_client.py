"""Tests del wake-on-demand de mineru-api."""

import pytest

from mineru_mcp import mineru_client
from mineru_mcp.tools import health


@pytest.mark.asyncio
async def test_ensure_running_noop_si_ya_responde(monkeypatch):
    """Si el backend ya está arriba no se invoca systemctl."""
    calls = []
    monkeypatch.setattr(mineru_client, "_reachable", _async_return(True))
    monkeypatch.setattr(mineru_client, "_systemctl", _systemctl_fake(calls))

    assert await mineru_client.ensure_running() is None
    assert calls == []


@pytest.mark.asyncio
async def test_ensure_running_arranca_y_espera(monkeypatch):
    """Backend caído: arranca el service y devuelve None cuando responde."""
    calls = []
    states = iter([False, False, True])
    monkeypatch.setattr(mineru_client, "_reachable", _async_return_seq(states))
    monkeypatch.setattr(mineru_client, "_systemctl", _systemctl_fake(calls))
    monkeypatch.setattr(mineru_client, "WAKE_POLL_S", 0)

    assert await mineru_client.ensure_running() is None
    assert calls == [("start", "mineru-api.service")]


@pytest.mark.asyncio
async def test_ensure_running_timeout(monkeypatch):
    """Si nunca responde, devuelve error en vez de colgarse."""
    monkeypatch.setattr(mineru_client, "_reachable", _async_return(False))
    monkeypatch.setattr(mineru_client, "_systemctl", _systemctl_fake([]))
    monkeypatch.setattr(mineru_client, "WAKE_POLL_S", 0)
    monkeypatch.setattr(mineru_client, "WAKE_TIMEOUT_S", 0.05)

    err = await mineru_client.ensure_running()
    assert err is not None
    assert "no respondió" in err
    assert "mineru-api.service" not in err


@pytest.mark.asyncio
async def test_health_inactivo_no_nombra_el_servicio(monkeypatch):
    """Backend dormido: el mensaje lo dice sin exponer el nombre del service."""
    async def _caido():
        raise ConnectionError("down")

    monkeypatch.setattr(mineru_client, "health", _caido)
    monkeypatch.setattr(mineru_client, "_systemctl", _systemctl_fake([], "inactive"))

    msg = await health.mineru_health()
    assert "inactivo" in msg
    assert "mineru-api.service" not in msg


@pytest.mark.asyncio
async def test_systemctl_sin_systemd_devuelve_127(monkeypatch):
    """En un contenedor no existe systemctl: no debe reventar la tool."""
    async def _sin_binario(*args, **kwargs):
        raise FileNotFoundError("systemctl")

    monkeypatch.setattr(mineru_client.asyncio, "create_subprocess_exec", _sin_binario)

    assert await mineru_client._systemctl("is-active", "x") == (127, "")


@pytest.mark.asyncio
async def test_ensure_running_sin_systemd_no_espera(monkeypatch):
    """Sin systemd no hay nada que arrancar: error inmediato en vez de 90s de polling."""
    monkeypatch.setattr(mineru_client, "_reachable", _async_return(False))
    monkeypatch.setattr(mineru_client, "_systemctl", _systemctl_fake([], rc=127))
    monkeypatch.setattr(mineru_client, "WAKE_TIMEOUT_S", 60)

    err = await mineru_client.ensure_running()
    assert "no hay systemd" in err
    assert mineru_client.MINERU_URL in err


@pytest.mark.asyncio
async def test_health_sin_systemd_reporta_la_url(monkeypatch):
    """En Docker el backend no está "dormido": simplemente no se alcanza."""
    async def _caido():
        raise ConnectionError("down")

    monkeypatch.setattr(mineru_client, "health", _caido)
    monkeypatch.setattr(mineru_client, "_systemctl", _systemctl_fake([], rc=127))

    msg = await health.mineru_health()
    assert msg.startswith("Error: no se puede contactar MinerU")


def _systemctl_fake(calls, stdout="", rc=0):
    async def _fn(*args):
        calls.append(args)
        return rc, stdout
    return _fn


def _async_return(value):
    async def _fn():
        return value
    return _fn


def _async_return_seq(it):
    async def _fn():
        return next(it)
    return _fn
