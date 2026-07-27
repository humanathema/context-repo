# context-repo

Shared, capacity-bounded semantic memory store. Full design rationale and
usage lives in [README.md](README.md) — read that first for the "why"
behind merge-on-conflict, capacity eviction, and confidence scores. This
file is the quick orientation for an AI session working *in* this repo.

## Layout

- `contextrepo/store.py` — the actual store: chromadb-backed, per-compartment
  collections, merge-on-conflict writes, capacity eviction. Everything else
  is a thin layer on top of this.
- `contextrepo/api.py` — FastAPI HTTP wrapper (`python run.py`, port 8420).
- `contextrepo/client.py` — CLI client for the HTTP API.
- `contextrepo/mcp_server.py` — MCP tool wrapper for Claude Code / other MCP
  agents. Runs `streamable-http` bound to `0.0.0.0:8421`, **no auth** —
  deliberate, so a second agent on another machine can reach the same
  store, but treat that port as untrusted-network-reachable.
- `contextrepo/ingest.py` — bulk-loads `CLAUDE.md`/`README.md`/`*handoff*.md`
  from a projects root into the store.
- `contextrepo/handoff.py` — drafts a handoff doc from git log/diffstat +
  recorded facts only, never generated prose. Use before running out of
  context mid-task.
- `tests/test_handoff.py` — the only test suite so far; covers
  `handoff.py`'s draft/mark-reviewed logic.
- `data/` — gitignored. chromadb's on-disk store + `handoff_state/`
  (per-repo last-reviewed-commit tracking). Never commit this.

## Working conventions

- The store is **non-generative by design** — it never composes text, only
  embeds/merges/retrieves what was actually written in. Don't add any code
  path that has the store or its wrappers generate prose from facts; that
  breaks the "can't hallucinate" guarantee the README leans on.
- `handoff.py` and `ingest.py` both explicitly produce **drafts for a human
  to review**, not autonomous writes to real handoff docs. Keep that
  boundary — don't wire either one to auto-commit or auto-edit a project's
  actual `HANDOFF.md`/`CLAUDE.md`.
- Run `pytest tests/` before committing changes to `store.py` or
  `handoff.py` — the merge-threshold and eviction behavior is easy to
  regress silently.
- `ingest.py`'s default (no `--allowlist`) walks every top-level folder
  under whatever root you give it. Since the MCP server has no auth, don't
  point it at a root containing anything sensitive without an allowlist.

## Second-agent protocol

See [ANTIGRAVITY_HANDOFF.md](ANTIGRAVITY_HANDOFF.md) for the protocol a
second, separately-running agent (e.g. Antigravity) should follow when
working in this repo — call `context_checkpoint` first, write material
decisions back via `context_write`.
