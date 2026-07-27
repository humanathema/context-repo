"""Walk a projects root, find convention docs (CLAUDE.md, *HANDOFF*.md,
README.md), and ingest them into context-repo so any connected AI session
has cross-project awareness without needing every doc's full text in its
own context window.

Two things get written:

1. One `project_index` fact per project — a short summary (what it is,
   where it lives, which docs were found) so `context_checkpoint
   ("project_index")` alone gives instant orientation across everything
   in the projects root.

2. The actual doc content, chunked by markdown heading, written into a
   per-project compartment (the project's folder name, slugified) — so a
   session working *in* that project can pull the real detail via
   context_query, not just the index summary.

Re-running this is safe and idempotent: unchanged chunks re-embed to
~1.0 similarity and merge in place (no duplicate growth) via context-
repo's existing merge-on-conflict behavior; only genuinely changed
content inserts/updates.

Usage:
    python -m contextrepo.ingest ~/Projects
    python -m contextrepo.ingest ~/Projects --dry-run
"""
import argparse
import re
from pathlib import Path

from contextrepo import store

# Filenames (case-insensitive) that count as "convention docs" worth ingesting.
DOC_PATTERNS = [
    "claude.md",
    "readme.md",
]
# Substring match for anything else handoff-shaped, e.g. ANTIGRAVITY_HANDOFF.md,
# HANDOFF.md, PROJECT_HANDOFF.md — deliberately loose since naming varies.
DOC_SUBSTRINGS = ["handoff"]

# Directories never worth descending into.
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".pytest_cache", "dist", "build", ".egg-info",
}

MAX_CHUNK_CHARS = 1200  # keep chunks small enough to be a useful, specific fact


def _is_doc(path: Path) -> bool:
    name = path.name.lower()
    if name in DOC_PATTERNS:
        return True
    return any(sub in name for sub in DOC_SUBSTRINGS) and name.endswith(".md")


def _iter_projects(root: Path, allowlist: set[str] | None):
    """Top-level directories under root, skipping hidden/junk dirs — each
    one treated as a project.

    If `allowlist` is given, ONLY those exact folder names are yielded —
    everything else (worktrees, backups, vendored third-party repos,
    anything not explicitly opted in) is skipped. This is deliberate:
    blacklisting noisy patterns keeps missing new cases (git worktrees,
    timestamped backup folders, vendored `repositories/` subtrees of
    unrelated projects), and some projects' docs (e.g. anything with
    production secrets/business data) shouldn't be swept into a store
    that's reachable over an unauthenticated tunnel just because they
    happen to live under the same root."""
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        if child.name.startswith(".") or child.name in SKIP_DIRS:
            continue
        if allowlist is not None and child.name not in allowlist:
            continue
        yield child


def _load_allowlist(path: Path) -> set[str]:
    lines = path.read_text().splitlines()
    return {line.strip() for line in lines if line.strip() and not line.strip().startswith("#")}


def _find_docs(project_dir: Path) -> list[Path]:
    found = []
    for path in project_dir.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if _is_doc(path):
            found.append(path)
    return found


def _chunk_markdown(text: str) -> list[str]:
    """Split on '##'-or-shallower headings; fall back to paragraph
    splitting for docs with no headings. Each chunk gets hard-capped so a
    single huge section doesn't become one unwieldy fact."""
    sections = re.split(r"\n(?=#{1,3}\s)", text.strip())
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= MAX_CHUNK_CHARS:
            chunks.append(section)
            continue
        # Oversized section: fall back to paragraph splitting within it.
        for para in section.split("\n\n"):
            para = para.strip()
            if para:
                chunks.append(para[:MAX_CHUNK_CHARS])
    return chunks


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9_-]", "_", name.lower()).strip("_-") or "default"


def ingest(root: Path, dry_run: bool = False, allowlist: set[str] | None = None) -> None:
    for project_dir in _iter_projects(root, allowlist):
        docs = _find_docs(project_dir)
        if not docs:
            continue

        compartment = _slug(project_dir.name)
        doc_names = [d.relative_to(project_dir).as_posix() for d in docs]

        index_fact = (
            f"{project_dir.name} ({project_dir}) has convention docs: "
            f"{', '.join(doc_names)}. Detail ingested into compartment "
            f"'{compartment}'."
        )
        print(f"[{project_dir.name}] docs found: {doc_names}")
        if not dry_run:
            store.write(compartment="project_index", content=index_fact,
                         key=project_dir.name)

        for doc_path in docs:
            try:
                text = doc_path.read_text(encoding="utf-8", errors="ignore")
            except OSError as exc:
                print(f"  ! could not read {doc_path}: {exc}")
                continue
            chunks = _chunk_markdown(text)
            rel = doc_path.relative_to(project_dir).as_posix()
            for chunk in chunks:
                content = f"[{rel}] {chunk}"
                if dry_run:
                    print(f"  would write ({len(content)} chars): {content[:80]}...")
                    continue
                result = store.write(compartment=compartment, content=content,
                                      key=rel)
                print(f"  {result['action']:9s} {rel}: {content[:60]}...")


def main() -> None:
    parser = argparse.ArgumentParser(description="ingest project docs into context-repo")
    parser.add_argument("root", help="projects root directory, e.g. ~/Projects")
    parser.add_argument("--dry-run", action="store_true",
                         help="show what would be ingested without writing")
    parser.add_argument("--allowlist", default=None,
                         help="path to a text file of project folder names to "
                              "include (one per line, '#' comments allowed). "
                              "If omitted, ALL top-level folders under root are "
                              "walked — only use that for a root you fully trust.")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"not a directory: {root}")

    allowlist = None
    if args.allowlist:
        allowlist = _load_allowlist(Path(args.allowlist).expanduser().resolve())
        print(f"allowlist: {sorted(allowlist)}")

    ingest(root, dry_run=args.dry_run, allowlist=allowlist)


if __name__ == "__main__":
    main()
