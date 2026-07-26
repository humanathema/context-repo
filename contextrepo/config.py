import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("CONTEXTREPO_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
EMBEDDING_MODEL = os.environ.get("CONTEXTREPO_MODEL", "all-MiniLM-L6-v2")

# Facts whose similarity to an existing node meets this threshold overwrite
# that node in place instead of being inserted as a new one. This is the
# "semantic slotting" behavior — updates replace, they don't accumulate.
MERGE_THRESHOLD = float(os.environ.get("CONTEXTREPO_MERGE_THRESHOLD", "0.86"))

# Per-compartment cap. Once exceeded, the least-recently-updated node is
# evicted so the store stays roughly constant size instead of growing
# unboundedly as more facts are written.
DEFAULT_CAPACITY = int(os.environ.get("CONTEXTREPO_CAPACITY", "500"))
