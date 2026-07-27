# Handoff — context-repo

Read this first, before doing any substantive work in this repo. See
[README.md](README.md) for full design rationale and [CLAUDE.md](CLAUDE.md)
for the file-layout orientation.

## Protocol for any second agent working here

1. **Call `context_checkpoint` for the relevant compartment before doing
   anything else.** It returns the most recently updated facts (recency,
   not similarity) — treat what it returns as binding decisions from prior
   sessions. Don't re-decide them without surfacing the conflict to the
   user first.
2. **After any material decision** — a scope call, something deliberately
   skipped or deferred, a discovered blocker — call `context_write` so the
   next session (whichever AI picks it up) has it without needing to
   re-read this whole file or the git log.
3. To register this project's MCP server (`context-repo`) with your own
   agent, point it at `python -m contextrepo.mcp_server` (stdio) or
   `http://localhost:8421` (streamable-http, if the server is already
   running) — check your own agent's settings for how it registers MCP
   servers; this repo doesn't touch that config.

## Current state (as of 2026-07-28)

- Core store + HTTP API + CLI client + MCP wrapper are in place and tested
  (`tests/test_handoff.py`, 3 tests passing).
- `contextrepo/mcp_server.py` was changed today from stdio-only to
  `streamable-http` bound to `0.0.0.0:8421`, **no authentication** — a
  deliberate, explicit choice to let a second agent reach the store from
  another machine. Anyone who can route to that port can read/write the
  store. Don't run this on an untrusted network.
- `contextrepo/ingest.py` was added today (bulk-loads `CLAUDE.md`/
  `README.md`/`*handoff*.md` docs from a projects root into the store) and
  was originally placed at the repo root; moved into `contextrepo/` so the
  documented `python -m contextrepo.ingest` invocation actually works.
- `contextrepo/handoff.py` was added today — drafts a handoff doc from git
  log/diffstat + recorded facts only (no generated prose), specifically to
  cover the failure mode of running out of context before writing a
  handoff. This file structure follows that same convention.
- Not yet done: no CI, no auth in front of the MCP/HTTP servers, no
  background "dream pass" consolidation, no distributed sharding (see
  README's "What this is *not*, yet" section — these are intentionally
  deferred, not overlooked).

## Open items for whoever picks this up next

- Nothing currently blocking. If you add auth to the MCP/HTTP servers,
  update the "no auth" warnings in README.md, CLAUDE.md, and this file —
  they're load-bearing for anyone deciding whether to run this on a shared
  network.
