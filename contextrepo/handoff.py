"""Drafts a handoff document from deterministic signal only — git history
and context-repo's own recorded facts — never generated prose. Built for
the concrete failure mode of running out of context/tokens before writing
a handoff and drifting several commits ahead of documentation.

This produces a DRAFT for you to review and fold into the real handoff
doc yourself, not a replacement for writing one — same "not yours to
decide unsupervised" principle used throughout this project's own
handoff conventions.

Usage:
    python -m contextrepo.handoff /path/to/repo compartment_name
    python -m contextrepo.handoff /path/to/repo compartment_name --mark-reviewed
"""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from contextrepo import store

_STATE_DIR = Path(__file__).resolve().parent.parent / "data" / "handoff_state"


def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return result.stdout.strip()


def _upstream_ref(repo: Path) -> str | None:
    ref = _run_git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    return ref if ref and "fatal" not in ref.lower() and "@{u}" not in ref else None


def _state_path(repo: Path) -> Path:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    return _STATE_DIR / f"{repo.name}.json"


def _last_marked_commit(repo: Path) -> str | None:
    path = _state_path(repo)
    if not path.exists():
        return None
    return json.loads(path.read_text()).get("last_commit")


def mark_reviewed(repo_path: str) -> dict:
    repo = Path(repo_path).resolve()
    head = _run_git(repo, "rev-parse", "HEAD")
    record = {"last_commit": head, "marked_at": datetime.now(timezone.utc).isoformat()}
    _state_path(repo).write_text(json.dumps(record))
    return record


def _commit_range(repo: Path) -> str | None:
    """A real 'base..HEAD' range when there's something to anchor to
    (upstream branch or a prior --mark-reviewed), else None — meaning
    there's no known baseline, only "show recent commits" makes sense."""
    upstream = _upstream_ref(repo)
    if upstream:
        return f"{upstream}..HEAD"
    last = _last_marked_commit(repo)
    if last:
        return f"{last}..HEAD"
    return None


def _git_signal(repo: Path) -> dict:
    commit_range = _commit_range(repo)
    if commit_range:
        log = _run_git(repo, "log", commit_range, "--oneline")
        base = commit_range.split("..")[0]
        diffstat = _run_git(repo, "diff", "--stat", base, "HEAD")
        range_label = commit_range
    else:
        log = _run_git(repo, "log", "--oneline", "-20")
        diffstat = ""
        range_label = "last 20 commits — no upstream or prior mark-reviewed to anchor to"

    uncommitted = _run_git(repo, "status", "--porcelain")
    return {
        "commit_range": range_label,
        "commits": [line for line in log.splitlines() if line],
        "diffstat": diffstat,
        "uncommitted_files": [line for line in uncommitted.splitlines() if line],
    }


def draft(repo_path: str, compartment: str, k_facts: int = 15) -> str:
    repo = Path(repo_path).resolve()
    git_signal = _git_signal(repo)
    facts = store.recent(compartment, k=k_facts)

    lines = [
        f"# Handoff draft — {repo.name}",
        f"_Generated {datetime.now(timezone.utc).isoformat()} from git history "
        "and context-repo facts only — no generated prose, review before using._",
        "",
        f"## Commits ({git_signal['commit_range']})",
    ]
    if git_signal["commits"]:
        lines.extend(f"- {c}" for c in git_signal["commits"])
    else:
        lines.append("_(none since last mark)_")
    lines.append("")

    if git_signal["uncommitted_files"]:
        lines.append("## Uncommitted changes")
        lines.extend(f"- {f}" for f in git_signal["uncommitted_files"])
        lines.append("")

    lines.append(f"## Recently recorded decisions (context-repo, compartment '{compartment}')")
    if facts:
        for f in facts:
            ts = f["metadata"].get("updated_at", "")
            lines.append(f"- ({ts}) {f['content']}")
    else:
        lines.append("_(nothing recorded yet in this compartment)_")
    lines.append("")

    lines.append("## Diffstat")
    lines.append("```")
    lines.append(git_signal["diffstat"] or "(no diff)")
    lines.append("```")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="draft a handoff doc from git + context-repo signal")
    parser.add_argument("repo_path")
    parser.add_argument("compartment")
    parser.add_argument("--k-facts", type=int, default=15)
    parser.add_argument("--out", default=None, help="write draft to this file instead of stdout")
    parser.add_argument("--mark-reviewed", action="store_true",
                         help="record current HEAD as the last-reviewed commit, so the next draft starts from here")
    args = parser.parse_args()

    if args.mark_reviewed:
        print(mark_reviewed(args.repo_path))
        return

    text = draft(args.repo_path, args.compartment, args.k_facts)
    if args.out:
        Path(args.out).write_text(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
