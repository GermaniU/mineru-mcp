"""Tests del wake-on-demand de mineru-api."""

import pytest

from mineru_mcp import mineru_client


@pytest.mark.asyncio
async def test_ensure_running_noop_si_ya_responde(monkeypatch):
    """Si el backend ya está arriba no se invoca systemctl."""
    calls = []
    monkeypatch.setattr(mineru_client, "_reachable", _async_return(True))
    monkeypatch.setattr(mineru_client.subprocess, "run", lambda *a, **k: calls.append(a))

    assert await mineru_client.ensure_running() is None
    assert calls == []


@pytest.mark.asyncio
async def test_ensure_running_arranca_y_espera(monkeypatch):
    """Backend caído: arranca el service y devuelve None cuando responde."""
    calls = []
    states = iter([False, False, True])
    monkeypatch.setattr(mineru_client, "_reachable", _async_return_seq(states))
    monkeypatch.setattr(mineru_client.subprocess, "run", lambda *a, **k: calls.append(a[0]))
    monkeypatch.setattr(mineru_client, "WAKE_POLL_S", 0)

    assert await mineru_client.ensure_running() is None
    assert calls == [["systemctl", "start", "mineru-api.service"]]


@pytest.mark.asyncio
async def test_ensure_running_timeout(monkeypatch):
    """Si nunca responde, devuelve error en vez de colgarse."""
    monkeypatch.setattr(mineru_client, "_reachable", _async_return(False))
    monkeypatch.setattr(mineru_client.subprocess, "run", lambda *a, **k: None)
    monkeypatch.setattr(mineru_client, "WAKE_POLL_S", 0)
    monkeypatch.setattr(mineru_client, "WAKE_TIMEOUT_S", 0.05)

    err = await mineru_client.ensure_running()
    assert err is not None
    assert "no respondió" in err


def _async_return(value):
    async def _fn():
        return value
    return _fn


def _async_return_seq(it):
    async def _fn():
        return next(it)
    return _fn
