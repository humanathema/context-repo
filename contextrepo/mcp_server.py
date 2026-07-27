"""MCP wrapper so a Claude Code (or other MCP-capable) session can read from
and write to the store as tools, instead of shelling out to the CLI. Runs
in-process against the same on-disk store the HTTP API and CLI use — no
HTTP hop required, just a shared data directory (see contextrepo/config.py,
CONTEXTREPO_DATA_DIR).

Register with Claude Code:
    claude mcp add context-repo -- /path/to/context-repo/.venv/bin/python -m contextrepo.mcp_server
"""
from mcp.server.fastmcp import FastMCP

from contextrepo import store

mcp = FastMCP("context-repo", host="0.0.0.0", port=8421)


@mcp.tool()
def context_write(compartment: str, content: str, key: str = "") -> dict:
    """Write a fact into a compartment of the shared context store. If it's
    semantically close enough to an existing fact in that compartment, it
    overwrites that fact in place (returned as action="merged") instead of
    being stored as a duplicate; otherwise it's inserted as a new fact
    (action="inserted")."""
    return store.write(compartment=compartment, content=content, key=key or None)


@mcp.tool()
def context_query(compartment: str, query: str, k: int = 5) -> dict:
    """Retrieve the top-k facts in a compartment closest in meaning to the
    query, each with a 0-1 cosine similarity score. The top-level
    `confidence` field is the best hit's score — treat a low confidence
    (e.g. well under 0.5) as a signal the store probably doesn't have what
    you're asking for, not as a weak-but-usable answer."""
    return store.query(compartment, query, k)


@mcp.tool()
def context_checkpoint(compartment: str, k: int = 10) -> dict:
    """Call this FIRST, before starting or continuing substantive work in a
    compartment — not just when something seems relevant. It returns the
    most recently recorded facts/decisions for that compartment, newest
    first. Treat these as binding prior decisions from other sessions
    (possibly a different AI or a different tool), not as suggestions to
    second-guess: if you're about to do something that conflicts with a
    fact returned here, stop and surface the conflict to the user rather
    than proceeding on your own judgment. If the list is empty, that itself
    is informative — no prior session has recorded anything here yet."""
    facts = store.recent(compartment, k)
    return {"compartment": compartment, "facts": facts, "count": len(facts)}


@mcp.tool()
def context_list_compartments() -> list:
    """List every compartment (namespace) in the store along with how many
    facts each currently holds."""
    return store.list_compartments()


@mcp.tool()
def context_forget(compartment: str, node_id: str) -> dict:
    """Delete a specific fact by id from a compartment."""
    return {"ok": store.forget(compartment, node_id)}

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
