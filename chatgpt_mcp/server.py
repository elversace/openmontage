"""Read-only MCP bridge for OpenMontage production information."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from backlot.state import PROJECTS_DIR, list_projects, load_board_state
from lib.paths import REPO_ROOT

mcp = FastMCP("OpenMontage", instructions="Read-only access: inspect pipelines and existing productions. Does not start or modify productions.")
_PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$")


def _project_dir(project_id: str) -> Path:
    if not _PROJECT_ID.fullmatch(project_id):
        raise ValueError("Invalid project id.")
    root = Path(PROJECTS_DIR).resolve()
    candidate = (root / project_id).resolve()
    if candidate.parent != root or not candidate.is_dir():
        raise ValueError("Project not found.")
    return candidate


@mcp.tool()
def list_video_pipelines() -> list[dict[str, Any]]:
    """List video production pipeline manifests installed in this checkout."""
    pipeline_dir = Path(REPO_ROOT) / "pipeline_defs"
    return [{"id": p.stem, "file": p.name} for p in sorted(pipeline_dir.glob("*.yaml"))]


@mcp.tool()
def list_productions() -> list[dict[str, Any]]:
    """List existing productions and their current progress."""
    return list_projects()


@mcp.tool()
def get_production_status(project_id: str) -> dict[str, Any]:
    """Read storyboard, stage progress, costs, and generated media for one production."""
    return load_board_state(_project_dir(project_id))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
