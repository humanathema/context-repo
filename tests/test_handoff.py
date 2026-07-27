import subprocess

import pytest

from contextrepo import config, handoff, store


def _run(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def temp_repo(tmp_path):
    repo = tmp_path / "demo_repo"
    repo.mkdir()
    _run(repo, "init", "-q")
    _run(repo, "config", "user.email", "test@example.com")
    _run(repo, "config", "user.name", "Test")
    (repo / "a.txt").write_text("v1\n")
    _run(repo, "add", "a.txt")
    _run(repo, "commit", "-q", "-m", "first commit")
    (repo / "a.txt").write_text("v2\n")
    _run(repo, "add", "a.txt")
    _run(repo, "commit", "-q", "-m", "second commit")
    return repo


def test_draft_includes_git_log_and_context_repo_facts(temp_repo, monkeypatch, tmp_path):
    monkeypatch.setattr(handoff, "_STATE_DIR", tmp_path / "handoff_state")
    # NOTE: contextrepo's chromadb client is a lazily-initialized module-level
    # singleton (see store.py's _get_client), so this only redirects storage
    # if no store.* call has happened yet anywhere in this test session —
    # true here since this is the first test in the suite to touch store.
    monkeypatch.setattr(config, "DATA_DIR", tmp_path / "cr_data")

    store.write("handoff_test_compartment", "decided to use markdown for the draft format")
    result = handoff.draft(str(temp_repo), "handoff_test_compartment")

    assert "second commit" in result
    assert "first commit" in result
    assert "decided to use markdown for the draft format" in result
    assert "handoff_test_compartment" in result


def test_draft_shows_uncommitted_changes(temp_repo):
    (temp_repo / "b.txt").write_text("untracked\n")
    result = handoff.draft(str(temp_repo), "some_other_compartment_no_facts")
    assert "Uncommitted changes" in result
    assert "b.txt" in result
    assert "nothing recorded yet" in result


def test_mark_reviewed_advances_commit_range(temp_repo):
    first_draft = handoff.draft(str(temp_repo), "compartment_x")
    assert "first commit" in first_draft
    assert "second commit" in first_draft

    handoff.mark_reviewed(str(temp_repo))

    (temp_repo / "a.txt").write_text("v3\n")
    _run(temp_repo, "add", "a.txt")
    _run(temp_repo, "commit", "-q", "-m", "third commit")

    second_draft = handoff.draft(str(temp_repo), "compartment_x")
    assert "third commit" in second_draft
    assert "first commit" not in second_draft
    assert "second commit" not in second_draft
