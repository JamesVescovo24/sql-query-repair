"""MCP stdio entry point; types and names are declared in contract.py."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import anyio
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from slimconfig import build_output, output_schema, plain_output

from contract import TOOLS, Tool
from plugin.logic import pin_reference, read_dataset, save_candidate

server = Server("sql-query-repair")
WORKSPACE_ENV = "NANOAGENT_WORKSPACE"
IMPLEMENTATIONS = {
    Tool.PIN: pin_reference,
    Tool.READ: read_dataset,
    Tool.SAVE: save_candidate,
}

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(name=tool.value, inputSchema=output_schema(given), outputSchema=output_schema(made))
        for tool, (given, made) in TOOLS.items()
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    tool = Tool(name)
    given, made = TOOLS[tool]
    workspace = Path(os.environ[WORKSPACE_ENV])
    output = IMPLEMENTATIONS[tool](build_output(arguments, given), workspace)
    if not isinstance(output, made):
        raise TypeError(f"{name} returned {type(output).__name__}, expected {made.__name__}")
    return plain_output(output)

def main() -> None:
    if WORKSPACE_ENV not in os.environ:
        raise SystemExit(f"{WORKSPACE_ENV} is not set")
    if set(IMPLEMENTATIONS) != set(Tool):
        raise SystemExit("Every declared tool must have an implementation")
    async def run() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    anyio.run(run)

if __name__ == "__main__":
    main()
