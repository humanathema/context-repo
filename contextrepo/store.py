"""Capacity-bounded semantic store. No generation happens here: writes are
embedded and either merged into the nearest existing node (if similar enough)
or inserted as a new one; reads return verbatim stored text plus a bounded
cosine-similarity score. Everything the store returns is something that was
actually written in, never something composed on the fly.

One Chroma collection per "compartment" (task/topic namespace), each capped
at a configurable size. When a compartment is full, the least-recently
updated node is evicted to make room — this is what keeps a compartment
roughly constant size instead of growing without bound as more facts land.
"""
import logging
import re
import threading
import uuid
from datetime import datetime, timezone

import chromadb
from chromadb.utils import embedding_functions

from contextrepo import config

logger = logging.getLogger(__name__)

_client_lock = threading.Lock()
_collection_lock = threading.Lock()
_client: chromadb.ClientAPI | None = None
_collections: dict[str, chromadb.Collection] = {}


def _get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                config.DATA_DIR.mkdir(parents=True, exist_ok=True)
                _client = chromadb.PersistentClient(path=str(config.DATA_DIR))
    return _client


def _sanitize(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]", "_", name.strip())
    slug = slug.strip("_-") or "default"
    return f"ctx_{slug}"[:63]


def _collection(compartment: str) -> chromadb.Collection:
    slug = _sanitize(compartment)
    if slug in _collections:
        return _collections[slug]
    with _collection_lock:
        if slug not in _collections:
            client = _get_client()
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=config.EMBEDDING_MODEL
            )
            _collections[slug] = client.get_or_create_collection(
                name=slug,
                embedding_function=ef,
                metadata={"hnsw:space": "cosine", "compartment": compartment},
            )
    return _collections[slug]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _evict_if_over_capacity(collection: chromadb.Collection, capacity: int) -> int:
    count = collection.count()
    if count <= capacity:
        return 0
    over = count - capacity
    all_rows = collection.get(include=["metadatas"])
    ids = all_rows["ids"]
    metas = all_rows["metadatas"]
    ranked = sorted(
        zip(ids, metas), key=lambda pair: pair[1].get("updated_at", "")
    )
    evict_ids = [node_id for node_id, _ in ranked[:over]]
    if evict_ids:
        collection.delete(ids=evict_ids)
    return len(evict_ids)


def write(
    compartment: str,
    content: str,
    key: str | None = None,
    capacity: int = config.DEFAULT_CAPACITY,
    merge_threshold: float = config.MERGE_THRESHOLD,
) -> dict:
    content = content.strip()
    if not content:
        raise ValueError("content must not be empty")

    collection = _collection(compartment)
    now = _now()

    match_id = None
    match_score = None
    if collection.count() > 0:
        result = collection.query(query_texts=[content], n_results=1)
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        if ids:
            match_id = ids[0]
            match_score = max(0.0, 1.0 - distances[0])

    if match_id is not None and match_score is not None and match_score >= merge_threshold:
        existing = collection.get(ids=[match_id], include=["metadatas"])
        prior_meta = existing["metadatas"][0] if existing["metadatas"] else {}
        version = int(prior_meta.get("version", 1)) + 1
        collection.upsert(
            ids=[match_id],
            documents=[content],
            metadatas=[{
                "key": key or prior_meta.get("key", ""),
                "created_at": prior_meta.get("created_at", now),
                "updated_at": now,
                "version": version,
            }],
        )
        return {"action": "merged", "id": match_id, "similarity": round(match_score, 3), "version": version}

    new_id = str(uuid.uuid4())
    collection.add(
        ids=[new_id],
        documents=[content],
        metadatas=[{
            "key": key or "",
            "created_at": now,
            "updated_at": now,
            "version": 1,
        }],
    )
    evicted = _evict_if_over_capacity(collection, capacity)
    return {"action": "inserted", "id": new_id, "evicted": evicted}


def query(compartment: str, query_text: str, k: int = 5) -> dict:
    collection = _collection(compartment)
    if collection.count() == 0:
        return {"results": [], "confidence": 0.0}

    n = min(k, collection.count())
    result = collection.query(query_texts=[query_text], n_results=n, include=["documents", "metadatas", "distances"])
    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    hits = []
    for node_id, doc, meta, dist in zip(ids, docs, metas, distances):
        hits.append({
            "id": node_id,
            "content": doc,
            "metadata": meta,
            "score": round(max(0.0, 1.0 - dist), 3),
        })

    confidence = hits[0]["score"] if hits else 0.0
    return {"results": hits, "confidence": confidence}


def forget(compartment: str, node_id: str) -> bool:
    collection = _collection(compartment)
    existing = collection.get(ids=[node_id])
    if not existing["ids"]:
        return False
    collection.delete(ids=[node_id])
    return True


def list_compartments() -> list[dict]:
    client = _get_client()
    out = []
    for coll in client.list_collections():
        meta = coll.metadata or {}
        out.append({
            "compartment": meta.get("compartment", coll.name),
            "count": coll.count(),
        })
    return out
