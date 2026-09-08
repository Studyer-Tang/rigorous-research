"""Codex-facing stdio MCP tools backed by the shared research kernel."""

import re
from pathlib import Path

from .core import Study


def study_path(root, slug):
    if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", slug):
        raise ValueError("study ID must be 1–80 lowercase letters, digits or hyphens")
    root = Path(root).resolve()
    path = root / slug
    if path.resolve().parent != root or path.is_symlink():
        raise ValueError("study must be directly inside the configured research root")
    return path


def server(root):
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError("Install rigorous-research[agent] to enable MCP") from exc
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    mcp = FastMCP(
        "rigorous-research",
        instructions="Use research_context, submit one typed proposal, then inspect results. Never promote drafts or calculations to proof verdicts.",
    )

    @mcp.tool()
    def research_create(study: str, objective: str, domain: str = "mathematics", network: bool = False) -> dict:
        """Create a persistent study with immutable original objective. Network enables literature retrieval."""
        study_path(root, study)
        return Study.create(root, study, objective, domain, network=network).state()

    @mcp.tool()
    def research_list() -> list[dict]:
        """List studies inside this server's configured research root."""
        return [
            {"study": p.name, "state": Study(study_path(root, p.name)).state()}
            for p in sorted(root.iterdir())
            if not p.is_symlink() and (p / "agent.sqlite3").is_file()
        ]

    @mcp.tool()
    def research_context(study: str) -> dict:
        """Read revision, objective, recent evidence, rejection feedback and the full proposal JSON schema."""
        return Study(study_path(root, study)).context()

    @mcp.tool()
    def research_submit(study: str, proposal: dict, revision: int, timeout: float = 30) -> dict:
        """Validate and execute one proposal from research_context.action_schema. No arbitrary shell execution."""
        return Study(study_path(root, study)).submit(proposal, revision, timeout)

    @mcp.tool()
    def research_asset(study: str, label: str, values: list[float]) -> dict:
        """Register user-provided numeric data and return its content hash; do not invent observations."""
        return Study(study_path(root, study)).add_asset(label, values)

    @mcp.tool()
    def research_inspect(study: str, action_id: int) -> dict:
        """Read a complete action and its certificate or diagnostic result, including older history."""
        return Study(study_path(root, study)).inspect(action_id)

    @mcp.tool()
    def research_pause(study: str, paused: bool = True) -> dict:
        """Pause between actions or resume; an already executing bounded tool may finish."""
        return Study(study_path(root, study)).pause(paused)

    @mcp.tool()
    def research_export(study: str) -> dict:
        """Export the complete research ledger. Original case proof and release gates still apply."""
        return Study(study_path(root, study)).export()

    return mcp


def serve(root):
    server(root).run(transport="stdio")
