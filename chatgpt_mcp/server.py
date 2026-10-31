"""OpenMontage MCP bridge: production preflight, guidance and guarded tool execution."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any
import jsonschema
from mcp.server.fastmcp import FastMCP
from backlot.state import PROJECTS_DIR, list_projects, load_board_state
from lib.paths import REPO_ROOT
from lib.pipeline_loader import load_pipeline
from lib.checkpoint import init_project
from tools.tool_registry import registry

mcp = FastMCP("OpenMontage", instructions=(
    "You are the production orchestrator. Run preflight, initialize a project, "
    "read each stage director skill, then execute tools stage by stage. Respect "
    "human approval gates. Before paid/consequential calls, state provider/model "
    "and estimate and obtain explicit user approval. Never silently switch providers."
))
_PROJECT_ID = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?$")
_TOOL_NAME = re.compile(r"^[a-z][a-z0-9_]{0,79}$")

def _project_dir(project_id: str) -> Path:
    if not _PROJECT_ID.fullmatch(project_id):
        raise ValueError("Invalid project id; use lowercase kebab-case.")
    root = Path(PROJECTS_DIR).resolve()
    candidate = (root / project_id).resolve()
    if candidate.parent != root or not candidate.is_dir():
        raise ValueError("Project not found.")
    return candidate

def _safe(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        from dataclasses import asdict
        value = asdict(value)
    if isinstance(value, Path): return str(value)
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()
                if str(k).lower() not in {"api_key","secret","password","token","authorization"}}
    if isinstance(value, (list, tuple)): return [_safe(v) for v in value]
    if isinstance(value, (str,int,float,bool)) or value is None: return value
    return str(value)

@mcp.tool()
def list_video_pipelines() -> list[dict[str, Any]]:
    """List available video production pipeline manifests."""
    folder = Path(REPO_ROOT) / "pipeline_defs"
    return [{"id": p.stem, "file": p.name} for p in sorted(folder.glob("*.yaml"))]

@mcp.tool()
def list_productions() -> list[dict[str, Any]]:
    """List existing productions and progress."""
    return list_projects()

@mcp.tool()
def get_production_status(project_id: str) -> dict[str, Any]:
    """Read storyboard, stage progress, costs and generated media."""
    return load_board_state(_project_dir(project_id))

@mcp.tool()
def production_preflight(pipeline_id: str) -> dict[str, Any]:
    """Validate pipeline and report stages, approval gates, provider availability and render runtimes."""
    manifest = load_pipeline(pipeline_id)
    registry.ensure_discovered()
    stages = [{"name": s["name"], "skill": s.get("skill"),
               "human_approval_required": bool(s.get("human_approval_default")),
               "required_tools": s.get("required_tools", []),
               "optional_tools": s.get("optional_tools", []),
               "tools_available": s.get("tools_available", []),
               "produces": s.get("produces", [])} for s in manifest.get("stages", [])]
    return {"pipeline": pipeline_id, "description": manifest.get("description"),
            "budget_default_usd": (manifest.get("orchestration") or {}).get("budget_default_usd"),
            "stages": stages, "capability_menu": registry.provider_menu_summary()}

@mcp.tool()
def initialize_production(project_id: str, title: str, pipeline_id: str, style_playbook: str = "") -> dict[str, Any]:
    """Create an empty project workspace; no generation and no provider spend."""
    if not _PROJECT_ID.fullmatch(project_id): raise ValueError("Use a lowercase kebab-case project id.")
    if not title.strip() or len(title) > 200: raise ValueError("Title must contain 1-200 characters.")
    manifest = load_pipeline(pipeline_id)
    folder = init_project(project_id, title=title.strip(), pipeline_type=pipeline_id,
                          style_playbook=style_playbook.strip() or None)
    return {"project_id": project_id, "pipeline": pipeline_id, "project_dir": str(folder),
            "stages": [s["name"] for s in manifest.get("stages", [])],
            "status": "initialized", "note": "Workspace only; no assets generated."}

@mcp.tool()
def get_stage_instructions(pipeline_id: str, stage_name: str) -> dict[str, Any]:
    """Read the manifest entry and director skill for a production stage."""
    manifest = load_pipeline(pipeline_id)
    stage = next((s for s in manifest.get("stages", []) if s.get("name") == stage_name), None)
    if stage is None: raise ValueError("Stage is not part of this pipeline.")
    result = {"pipeline": pipeline_id, "stage": stage_name, "manifest_stage": stage}
    skill = stage.get("skill")
    if skill:
        root = (Path(REPO_ROOT) / "skills").resolve()
        path = (root / (skill + ".md")).resolve()
        if root not in path.parents: raise ValueError("Invalid skill path.")
        result["director_instructions"] = path.read_text(encoding="utf-8") if path.is_file() else None
    return result

@mcp.tool()
def get_tool_catalog(capability: str = "") -> list[dict[str, Any]]:
    """Discover tools with provider, schema, dependency, status and skill metadata."""
    registry.ensure_discovered()
    tools = registry.get_by_capability(capability) if capability else [registry.get(n) for n in registry.list_all()]
    return [_safe(t.get_info()) for t in tools if t is not None]

@mcp.tool()
def estimate_production_tool(tool_name: str, inputs: dict[str, Any]) -> dict[str, Any]:
    """Check dependencies and validate inputs, then estimate cost without executing."""
    if not _TOOL_NAME.fullmatch(tool_name): raise ValueError("Invalid tool name.")
    registry.ensure_discovered()
    tool = registry.get(tool_name)
    if tool is None: raise ValueError("Unknown registered tool.")
    tool.check_dependencies()
    if tool.input_schema: jsonschema.validate(instance=inputs, schema=tool.input_schema)
    return _safe(tool.dry_run(inputs))

@mcp.tool()
def execute_production_tool(tool_name: str, inputs: dict[str, Any], user_approved_cost_usd: float = 0.0) -> dict[str, Any]:
    """Execute one registered tool only after a fresh estimate and explicit user-approved USD ceiling."""
    if not _TOOL_NAME.fullmatch(tool_name): raise ValueError("Invalid tool name.")
    if user_approved_cost_usd < 0: raise ValueError("Approval ceiling cannot be negative.")
    registry.ensure_discovered()
    tool = registry.get(tool_name)
    if tool is None: raise ValueError("Unknown registered tool.")
    tool.check_dependencies()
    if tool.input_schema: jsonschema.validate(instance=inputs, schema=tool.input_schema)
    quote = tool.dry_run(inputs)
    estimate = quote.get("estimated_cost_usd")
    if estimate is None: raise ValueError("Reliable quote unavailable; execution blocked.")
    if float(estimate) > float(user_approved_cost_usd):
        raise ValueError("Approved cost ceiling is below estimate; obtain user approval first.")
    return _safe(tool.execute(inputs))

def main() -> None:
    mcp.run(transport="stdio")

if __name__ == "__main__": main()
