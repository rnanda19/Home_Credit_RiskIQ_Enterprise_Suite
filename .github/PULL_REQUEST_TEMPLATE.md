## What does this PR do?

## Which notebook(s) / module(s) / service(s) does it touch?

## Checklist

- [ ] `make test-all` passes locally (`notebook-check` + `test` + `lint` + `security`)
- [ ] If a notebook changed: it was actually executed end-to-end
      (`jupyter nbconvert --execute`) against a real or synthetic dataset —
      not just edited — and produced 0 errors before this PR was opened
- [ ] If a notebook changed: code-cell outputs and `execution_count` were
      cleared before committing (`nbformat`-clean diff, no stale output baked in)
- [ ] If `src/` changed: any notebook or service that imports the changed
      module was re-run/re-tested, not just the module in isolation
- [ ] If a service's request/response shape changed: `tests/test_scoring_services.py`
      was updated to match, and still passes
- [ ] If a claimed number (accuracy, speedup, dollar impact, etc.) is new or
      changed: it was actually measured, and the method is stated in the PR
      description — no invented or approximate figures presented as measured
- [ ] Docs updated if relevant (root README, per-project README, MODEL_CARD.md,
      CHANGELOG.md, BENCHMARKS.md)

## How was this tested?

## Anything reviewers should pay special attention to?
