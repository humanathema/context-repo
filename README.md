# context-repo

A shared, capacity-bounded semantic memory that multiple AI sessions (or
tools) can plug into — write facts in from one session, read them back in
another — without every AI needing the full history in its own context
window.

It is deliberately **non-generative**: the store never composes text. A
write is embedded and either merged into the most similar existing fact (if
similarity is high enough) or inserted as a new one; a query returns the
verbatim stored facts that are semantically closest to it, each with a
bounded cosine-similarity score. Nothing here can hallucinate a fact, because
nothing here writes prose — it only stores and retrieves what was actually
put in.

## Why this shape

- **Compartments** are namespaces (e.g. one per task, project, or
  conversation thread) so an AI session can plug into just the slice
  relevant to it, or into everything.
- **Merge-on-conflict**: writing a fact that's semantically close enough to
  one already stored overwrites it in place (bumping a version + timestamp)
  instead of appending a duplicate. This is what keeps a compartment from
  growing without bound just because the same fact gets restated across
  sessions.
- **Capacity eviction**: each compartment has a cap (default 500 nodes).
  Once full, the least-recently-updated node is evicted to make room for new
  writes. Combined with merge-on-conflict, this is the "roughly constant
  size" behavior — old, stale, unreferenced facts get displaced by new or
  frequently-reinforced ones over time.
- **Confidence signal**: every query returns a `confidence` value (the top
  hit's cosine similarity). A low number is a legitimate signal that the
  store probably doesn't have what's being asked for — surface that to the
  user or the calling AI rather than treating an empty/weak result as
  silence.

## What this is *not*, yet

This is the MVP: a store + HTTP API + CLI client, meant to be run on one
machine and queried by whatever AI sessions can reach it. It does not (yet)
do public exposure/auth, background consolidation ("dream" passes that
periodically re-merge nearby facts), or distributed sharding across multiple
devices. Those are natural next stages once the basic loop is proven useful
day to day — see the "why this shape" reasoning above for how they'd hook
into the same merge/eviction mechanics rather than needing a redesign.

## Quickstart

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e .
python run.py            # http://localhost:8420
```

In another terminal:

```bash
python -m contextrepo.client write thesis "Nash's honours thesis has no hard deadline"
python -m contextrepo.client write thesis "The dev machine has 8GB RAM, real OOM risk on full-corpus scripts"
python -m contextrepo.client query thesis "how much memory does the dev machine have"
python -m contextrepo.client compartments
```

Writing a fact that's close enough to one already stored merges instead of
duplicating:

```bash
python -m contextrepo.client write thesis "the dev machine has 8 gigabytes of RAM"
# -> {"action": "merged", "id": "...", "similarity": 0.86x, "version": 2}
```

The merge threshold (default 0.86 cosine similarity) is a real, tunable
trade-off: too low and unrelated facts collapse into each other; too high
and near-duplicate restatements just pile up as separate nodes. `all-MiniLM`
does not consider "the dev box has 8GB of RAM" and "the dev machine has 8GB
RAM, real OOM risk on full-corpus scripts" similar enough to merge (0.61) —
correctly, since the second sentence carries an extra clause the first
doesn't. Expect to tune `merge_threshold` per compartment as you see how it
behaves on your own material.

## API

- `POST /write {compartment, content, key?, capacity?, merge_threshold?}` —
  insert or merge a fact.
- `POST /query {compartment, query, k?}` — top-k facts with a `confidence`
  score.
- `GET /compartments` — list compartments and their sizes.
- `DELETE /compartments/{compartment}/nodes/{node_id}` — forget a fact.

Any AI tool that can make an HTTP call can use this directly — there's no
SDK requirement.

## MCP (Claude Code / Claude Desktop)

`contextrepo/mcp_server.py` exposes the store as four MCP tools
(`context_write`, `context_query`, `context_list_compartments`,
`context_forget`), running in-process against the same on-disk store the
HTTP API uses — no server needs to be running separately.

```bash
pip install -e ".[mcp]"
claude mcp add context-repo -- /path/to/context-repo/.venv/bin/python -m contextrepo.mcp_server
```

Then any Claude Code session can write and query facts as tool calls
directly, without shelling out to the CLI or running a second process.
