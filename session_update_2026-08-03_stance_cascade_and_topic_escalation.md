# Session update — 2026-08-03 — stance cascade + topic-escalation

Full detail in ConspiracyComments/handoff/task_2026-08-03_session_handoff_stance_cascade_and_topic_escalation.md.
This is the compressed, ingestible summary.

## Facts worth remembering across sessions

- **round7-combined-fixes is the current best stance classifier: kappa 0.4760** (entity-conditioning
  `[ENTITY: X]` prefix + bucket-redesign 3-way stage2, on round7's full random-expansion training
  data), measured on a 680-row val — up from a 297-334 row val this session established was too
  small to trust. Old "best so far" numbers (round2=0.4922, round7-old=0.4601) did NOT survive
  the bigger val (round2→0.4207, round7-plain→0.4198) — treat any pre-2026-08-03 stance kappa as
  unverified against the current val.
- Only ~2,266 human-labeled rows exist across this project's ENTIRE history. Everything beyond
  that in the "18k+ train rows" is AI-silver (frontier-judge-scored), not human-labeled.
- Two real architecture wins (entity-conditioning +0.0548, bucket-redesign +0.0677 kappa,
  independently ablation-tested weeks ago) were never folded into the production round2-7
  pipeline until this session. Only pay off on the fuller-data rounds (round6/7), not the
  boundary-heavy smaller ones (round2/5).
- Cascade/escalation to a frontier judge (Gemini) is real but was originally overstated — a
  212-row-val simulation showed 0.49→0.71 kappa; correctly measured on 680 rows it's 0.43→0.55-0.56,
  and only ever fixes stage2 (hostile-vs-endorsement) errors, never stage1 (other-vs-not) errors,
  since escalation structurally never touches stage1's own decision. Stage1 is the real
  bottleneck everywhere (oracle-ceiling test: 0.89 achievable if stage1 were perfect, vs ~0.53-0.58
  actually achieved).
- `EMPATH_PATH` (`data/processed/empath_scores_full_mapped.parquet`) has never been downloaded
  locally in this project (only exists on Kaggle) — any local script that depends on it silently
  degrades to empty/missing behavior rather than erroring. Watch for this pattern recurring.
- Machine has real, tight local disk space (~20GB free after cleanup this session, was down to
  ~1.8GB at the worst point). A full local index of the raw comment corpus is genuinely ~18GB —
  don't build one; use targeted/scoped extraction instead.
- 4-account Kaggle multi-account orchestration is in active use
  (`~/.surge-compute/providers.yaml`: tobiasnashws/tobiasnash/tobiasnashktc/manawatusamaritans),
  each account capped at 2 concurrent GPU sessions. Cross-account `kernel_sources` needs the
  source kernel's Sharing set to Public via the website (no CLI/API toggle exists without a full
  rerun).

## Open as of this update

- model-size-ablation (round5 + round7, ModernBERT-large + entity-span windowing), ensemble test
  (fixed decision-rule version), and the topic-modeling exact-escalation-count recompute kernel
  were all still running when this was written — check Kaggle directly for current state, don't
  trust any number from these as final without re-verifying.
- Progressive distillation cascade (escalation + human review → periodic stage1 retrain,
  specifically targeting the confirmed bottleneck) designed but not launched.
- Full-corpus topic-modeling escalation (divergence-flagging + outlier-coherence discovery at
  scale) blocked on the exact-count recompute kernel finishing; cost estimate ~$93 pending sign-off.
