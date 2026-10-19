"""Demo grabable: el agente convierte un PDF real en Markdown vía MCP.

Habla MCP de verdad contra un server mineru-mcp en modo HTTP: primero
mineru_health y después parse_document de dos páginas de "Attention Is All You
Need" (arXiv:1706.03762), enviadas en base64 como lo haría un cliente remoto.
Muestra un extracto del Markdown que devuelve MinerU. Es la fuente de
docs/assets/demo.gif.

Requiere un server mineru-mcp escuchando en MCP_DEMO_URL — por defecto el puerto
del server, http://localhost:8202/mcp — con MINERU_URL apuntando a un mineru-api
real. El PDF se descarga de arXiv salvo que MCP_DEMO_PDF apunte a una copia local.

Uso:
    python scripts/demo_parse.py
    MCP_DEMO_URL=http://localhost:8299/mcp MCP_DEMO_PDF=attention.pdf python scripts/demo_parse.py
"""

from __future__ import annotations

import asyncio
import base64
import os
import re
import sys
import textwrap
import time
from pathlib import Path

import httpx
from fastmcp import Client

URL = os.environ.get("MCP_DEMO_URL", "http://localhost:8202/mcp")
PDF_URL = "https://arxiv.org/pdf/1706.03762"
# Páginas 5 y 6 del paper (MinerU cuenta desde 0): la FFN con su ecuación y la Tabla 1.
START_PAGE, END_PAGE = 4, 5
WIDTH = 84


def out(text: str = "") -> None:
    print(text, flush=True)


async def beat(seconds: float = 0.6) -> None:
    await asyncio.sleep(seconds)


def load_pdf() -> bytes:
    local = os.environ.get("MCP_DEMO_PDF")
    if local:
        return Path(local).read_bytes()
    r = httpx.get(PDF_URL, follow_redirects=True, timeout=60)
    r.raise_for_status()
    return r.content


def text_of(result) -> str:
    return result.content[0].text


def excerpt(md: str) -> list[str]:
    """Un título con su párrafo y su ecuación, y las primeras filas de una tabla."""
    lines = []
    heading = re.search(r"^#+ .*Feed-Forward.*$", md, re.MULTILINE) or re.search(
        r"^#+ .+$", md, re.MULTILINE
    )
    if heading:
        lines.append("\033[1m" + heading.group(0) + "\033[0m")
        rest = md[heading.end() :].lstrip("\n")
        paragraph = textwrap.wrap(rest.split("\n\n", 1)[0].replace("\n", " "), WIDTH)
        lines += paragraph[:2]
        if len(paragraph) > 2:
            lines[-1] += " …"
        formula = re.search(r"\$\$\s*(.+?)\s*\$\$", rest, re.DOTALL)
        if formula:
            latex = "$$ " + " ".join(formula.group(1).split()) + " $$"
            lines += [
                "\033[33m" + line + "\033[0m" for line in textwrap.wrap(latex, WIDTH)
            ]
    table = re.search(r"<table>.*?</table>", md, re.DOTALL)
    if table:
        lines.append("")
        for row in re.findall(r"<tr>(.*?)</tr>", table.group(0), re.DOTALL)[:3]:
            cells = [
                c.strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            ]
            text = " │ ".join(cells)
            lines.append(
                "\033[36m"
                + (text if len(text) <= WIDTH else text[: WIDTH - 1] + "…")
                + "\033[0m"
            )
    return lines


async def main() -> int:
    pdf = load_pdf()
    out()
    out(
        "  \033[1mMinerU MCP\033[0m — el agente convierte un PDF en Markdown, en tu propio server"
    )
    out(
        "  \033[2m─────────────────────────────────────────────────────────────────────────\033[0m"
    )
    await beat()
    async with Client(URL, timeout=300) as c:
        out("  \033[2magent →\033[0m mineru_health")
        await beat()
        health = text_of(await c.call_tool("mineru_health", {}))
        # La URL de mineru-api es del host, no aporta nada a la demo.
        shown = [
            line
            for line in health.splitlines()
            if not line.startswith(("URL:", "Status:"))
        ]
        out("  \033[2mserver ←\033[0m " + " · ".join(shown[:3]))
        await beat()
        out()
        out(
            "  \033[2magent →\033[0m parse_document  "
            f'{{ file_name: "attention.pdf", start_page: {START_PAGE}, end_page: {END_PAGE} }}'
        )
        started = time.monotonic()
        res = text_of(
            await c.call_tool(
                "parse_document",
                {
                    "file_base64": base64.b64encode(pdf).decode(),
                    "file_name": "attention.pdf",
                    "start_page": START_PAGE,
                    "end_page": END_PAGE,
                    "lang": "en",
                },
            )
        )
        elapsed = time.monotonic() - started
    if res.startswith(("Error", "BLOQUEADO", "MinerU no")):
        out("  \033[1;31mserver ←\033[0m " + res[:300])
        return 1
    backend = re.search(r"\*\*Backend:\*\* (\S+)", res)
    md = res.split("\n\n", 2)[-1] if backend else res
    out(
        f"  \033[2mserver ←\033[0m {END_PAGE - START_PAGE + 1} páginas → "
        f"{len(md.encode()) / 1024:.1f} KB de Markdown "
        f"en {elapsed:.1f} s  (backend {backend.group(1) if backend else '?'})"
    )
    await beat()
    out()
    for line in excerpt(md):
        out("    " + line)
    await beat()
    equations = len(re.findall(r"\$\$", md)) // 2
    tables = md.count("<table")
    out()
    out(
        f"  \033[1;32m✓ {equations} ecuaciones en LaTeX · {tables} tabla en HTML — "
        "el cliente no instaló PyTorch ni modelos\033[0m"
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
