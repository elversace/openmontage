# ChatGPT MCP bridge (experimental, read-only)

This branch adds a local stdio MCP server for inspecting an OpenMontage checkout.

## Exposed tools

- list_video_pipelines — list pipeline manifests installed in this checkout.
- list_productions — list existing productions and their progress.
- get_production_status — read one production's Backlot state.

The bridge is intentionally read-only. It does not generate a video, start a pipeline, approve a creative gate, or write project files. OpenMontage currently relies on an AI coding agent as its production orchestrator; exposing a safe production-start action requires a separate execution and approval design.

## Local installation

Install the project dependencies, including the MCP SDK:

    python -m pip install -e .

Run the server from the OpenMontage repository root:

    python -m chatgpt_mcp.server

The server uses MCP stdio transport and is intended for a local MCP-capable host. Do not expose it directly to the public internet.

## ChatGPT compatibility

A local stdio server is not automatically connected to ChatGPT. ChatGPT custom MCP connections require a reachable HTTPS MCP endpoint and are subject to plan and client availability. This repository change does not deploy a public endpoint or create a paid hosting resource.

## Security

- Project identifiers are validated before filesystem access.
- Project paths are resolved beneath the configured OpenMontage projects directory.
- The bridge exposes read-only tools only.
- No API keys or environment-file values are returned.
