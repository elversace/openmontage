# ChatGPT MCP bridge (experimental)

This branch exposes the OpenMontage pipeline system to an MCP-capable AI client. The AI client remains the creative and production orchestrator, following `AGENT_GUIDE.md`, pipeline manifests, director skills, checkpoint governance, and tool contracts.

## MCP tools

### Read and plan
- `list_video_pipelines` — installed pipeline manifests.
- `list_productions` / `get_production_status` — Backlot production state.
- `production_preflight(pipeline_id)` — validates a pipeline and returns its stages, human approval gates, provider availability, setup requirements, and render-runtime availability.
- `get_stage_instructions(pipeline_id, stage_name)` — returns the stage manifest entry and its director skill.
- `get_tool_catalog(capability?)` — registered tool schemas, status, provider, dependencies, and Layer 3 skill references.

### Production execution
- `initialize_production(project_id, title, pipeline_id, style_playbook?)` — creates the project workspace only. It does not generate media or spend money.
- `estimate_production_tool(tool_name, inputs)` — validates tool inputs and checks dependencies/cost without executing.
- `execute_production_tool(tool_name, inputs, user_approved, user_approved_cost_usd)` — executes one registered OpenMontage tool only when explicit approval is true. It rechecks dependencies, validates the input schema, obtains a fresh dry-run estimate, and refuses execution if the quote is unavailable or exceeds the supplied user-approved ceiling. Explicit approval is required even for tools estimated at $0.

## Required orchestration sequence

1. Run `production_preflight` and present the real provider/runtime menu and estimated budget.
2. Initialize a project workspace.
3. For each stage in manifest order, call `get_stage_instructions` and follow the returned director skill and all referenced meta/Layer 3 skills.
4. Respect every `human_approval_default: true` gate. Do not advance until the user explicitly approves the relevant artifact/decision.
5. Before a paid or consequential tool call, state its exact tool/provider/model, purpose, whether it is a sample or batch, and the estimate. Obtain explicit user approval in chat, then pass the approved USD ceiling to `execute_production_tool`.
6. Execute one tool at a time, inspect its result, write/validate stage artifacts and checkpoints using the OpenMontage checkpoint protocol, then continue.
7. Run post-render review and present the final output only when validation passes.

The MCP bridge does not silently choose replacement providers, skip approvals, or invent a successful render. The current execution tool is deliberately one registered tool call at a time; it is not a background job runner.

## Local installation

Install the project dependencies, including the MCP SDK:

    python -m pip install -e .

Run from the repository root:

    python -m chatgpt_mcp.server

The server currently uses MCP stdio transport. A local stdio server is not automatically connected to ChatGPT.

## ChatGPT connectivity

A ChatGPT custom MCP connection needs a reachable HTTPS MCP endpoint or secure tunnel and is subject to plan/client availability. This branch does not deploy a public endpoint, create a paid hosting resource, or modify the default branch. Custom MCP connections are not currently supported in the ChatGPT iOS app; configure/test through the supported ChatGPT web experience and verify plan eligibility before investing in hosting.

## Security and cost controls

- Project IDs are restricted to lowercase kebab-case and project paths are resolved beneath the configured projects directory.
- Tool names are validated and only tools discovered in the OpenMontage registry can execute.
- Tool inputs are validated against each registered input schema when one exists.
- Execution requires an explicit approval flag, a fresh dry-run quote, and a user-approved USD ceiling. Unknown quotes and estimates above that ceiling are rejected; approval is required even for tools estimated at $0. API/hybrid tools that inherit the base placeholder cost of $0 are treated as unquoted and blocked until they implement an explicit estimator.
- Secrets are filtered from returned tool metadata/results; environment files and secret values are never intentionally exposed.
- The MCP server must remain private. Do not expose stdio directly or publish an unauthenticated HTTP endpoint.
- Tool execution can still trigger external provider charges up to the approved ceiling. The caller must obtain user approval before invoking it.
