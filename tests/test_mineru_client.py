"""Tests del wake-on-demand de mineru-api."""

import importlib

import pytest

from mineru_mcp import config, mineru_client
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


@pytest.mark.asyncio
async def test_systemctl_scope_user_agrega_flag(monkeypatch):
    """Default: mineru-api es unit de usuario, así que va con --user."""
    calls = _exec_fake(monkeypatch)
    monkeypatch.setattr(mineru_client, "MINERU_SYSTEMCTL_SCOPE", "user")

    rc, out = await mineru_client._systemctl("start", "mineru-api.service")
    assert (rc, out) == (0, "active")
    assert calls == [("systemctl", "--user", "start", "mineru-api.service")]


@pytest.mark.asyncio
async def test_systemctl_scope_system_sin_flag(monkeypatch):
    """Con scope system se llama como antes, sin --user."""
    calls = _exec_fake(monkeypatch)
    monkeypatch.setattr(mineru_client, "MINERU_SYSTEMCTL_SCOPE", "system")

    await mineru_client._systemctl("is-active", "mineru-api.service")
    assert calls == [("systemctl", "is-active", "mineru-api.service")]


@pytest.mark.asyncio
async def test_health_consulta_el_scope_configurado(monkeypatch):
    """El health pregunta is-active en el mismo scope que el wake."""
    calls = _exec_fake(monkeypatch, stdout=b"inactive\n", rc=3)
    monkeypatch.setattr(mineru_client, "MINERU_SYSTEMCTL_SCOPE", "user")
    monkeypatch.setattr(mineru_client, "health", _caido)

    assert "inactivo" in await health.mineru_health()
    assert calls == [("systemctl", "--user", "is-active", "mineru-api.service")]


async def _caido():
    raise ConnectionError("down")


@pytest.mark.parametrize("valor", ["usr", "global", "--user"])
def test_scope_invalido_falla_al_arrancar(monkeypatch, valor):
    """Un scope mal escrito no debe caer en silencio a uno de los dos modos."""
    monkeypatch.setenv("MINERU_SYSTEMCTL_SCOPE", valor)
    try:
        with pytest.raises(ValueError, match="MINERU_SYSTEMCTL_SCOPE"):
            importlib.reload(config)
    finally:
        monkeypatch.delenv("MINERU_SYSTEMCTL_SCOPE")
        importlib.reload(config)


@pytest.mark.parametrize(("valor", "esperado"), [(" System ", "system"), ("", "user")])
def test_scope_normaliza_y_vacio_es_user(monkeypatch, valor, esperado):
    monkeypatch.setenv("MINERU_SYSTEMCTL_SCOPE", valor)
    try:
        assert importlib.reload(config).MINERU_SYSTEMCTL_SCOPE == esperado
    finally:
        monkeypatch.delenv("MINERU_SYSTEMCTL_SCOPE")
        importlib.reload(config)


def _exec_fake(monkeypatch, stdout=b"active\n", rc=0):
    calls = []

    class _Proc:
        returncode = rc

        async def communicate(self):
            return stdout, b""

    async def _fn(*args, **kwargs):
        calls.append(args)
        return _Proc()

    monkeypatch.setattr(mineru_client.asyncio, "create_subprocess_exec", _fn)
    return calls


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
