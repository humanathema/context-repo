"""HTTP surface so any AI session (or tool with an HTTP/MCP client) can read
from and write to the shared store. Every response is either verbatim stored
text or a similarity score computed from it — nothing here generates prose."""
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from contextrepo import config, store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="context-repo", version="0.1.0")


class WriteRequest(BaseModel):
    compartment: str
    content: str
    key: str | None = None
    capacity: int = config.DEFAULT_CAPACITY
    merge_threshold: float = config.MERGE_THRESHOLD


class QueryRequest(BaseModel):
    compartment: str
    query: str
    k: int = 5


@app.post("/write")
def write(req: WriteRequest) -> dict:
    try:
        return store.write(
            compartment=req.compartment,
            content=req.content,
            key=req.key,
            capacity=req.capacity,
            merge_threshold=req.merge_threshold,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/query")
def query(req: QueryRequest) -> dict:
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")
    return store.query(req.compartment, req.query, req.k)


@app.get("/compartments/{compartment}/checkpoint")
def checkpoint(compartment: str, k: int = 10) -> dict:
    facts = store.recent(compartment, k)
    return {"compartment": compartment, "facts": facts, "count": len(facts)}


@app.delete("/compartments/{compartment}/nodes/{node_id}")
def forget(compartment: str, node_id: str) -> dict:
    ok = store.forget(compartment, node_id)
    if not ok:
        raise HTTPException(status_code=404, detail="node not found")
    return {"ok": True}


@app.get("/compartments")
def compartments() -> list[dict]:
    return store.list_compartments()


@app.get("/health")
def health() -> dict:
    return {"ok": True}
