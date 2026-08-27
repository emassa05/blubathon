# Faro contract handoffs (P1 to P2)

P1 publishes contracts here. P2 consumes them without copying or editing them
(CONVENTIONS 5). If P2 needs a change, the request goes back with route,
operation, literal request JSON, literal response JSON, the reason, and a failing
consumer test; P1 then edits the model, the generated artifacts and the examples
in one change (TAREAS 3.2).

The machine-readable handoff is
[`generated/contract.lock.json`](generated/contract.lock.json). It carries
`contract_version`, `schema_hash`, the published model list, the artifact list,
the example list and the commands that reproduce all of it. Read it there rather
than from this page: a hash copied into prose goes stale.

---

## H1 - executable contract (M1)

**Status:** published.

### What is in it

| Artifact | Path |
|---|---|
| Pydantic source of truth | `packages/shared/domain/**`, re-exported by `packages/shared/models.py` |
| Constants C01-C50 | `packages/shared/constants.py` |
| Field catalogue and source matrix | `packages/shared/field_catalog.py` |
| Canonical bytes, hashes, windows | `packages/shared/canonical.py` |
| Append-only projection | `packages/shared/projection.py` |
| Spanish copy | `packages/shared/texts.py` |
| JSON Schema bundle | `packages/shared/generated/faro.schema.json` |
| TypeScript types | `packages/shared/generated/contract.ts` |
| Zod schemas | `packages/shared/generated/contract.zod.ts` |
| Constants for the frontend | `packages/shared/generated/constants.ts` |
| Field catalogue for the frontend | `packages/shared/generated/field-catalog.ts` |
| Spanish copy for the frontend | `packages/shared/generated/texts.ts` |
| Valid and invalid examples | `packages/shared/examples/` |

### Regenerating

```text
python -m tools.contracts.generate
python -m tools.contracts.examples
git diff --exit-code packages/shared/generated packages/shared/examples
```

Nothing under `generated/` is edited by hand. `examples/` is rendered from the
models, so a published example cannot drift from the published contract.

### How to consume it from `apps/web`

`packages/shared/generated/index.ts` re-exports the types, the Zod schemas, the
constants, the field catalogue and the Spanish copy. The frontend needs `zod` as
a dependency and should import from that index rather than restating a type, a
threshold, a source matrix row or a piece of visible copy.

### What the contract will not let you build

- An abstention with a probability, an interval, a band or a narrative.
- A simulation score presented as a clinical probability.
- Any exposure of the shadow challenger.
- A default shown inside an audited session.
- An episode created when no target definition is selectable.
- A `no` or `unknown` report that closes a window early.
- A resolution that was ever conflicted pretending it is clean.
- A human plan carrying RAG citations.
- An idempotency scope built from a route template instead of a concrete path.

Each of these has an invalid example under `packages/shared/examples/invalid/`
naming the SPEC rule it breaks.

---

## Open requests to P2

1. **`tests/conftest.py` still imports the retired v0.2 modules.** It is the
   global fixture TAREAS assigns to P2 for removal in P2.2. Until it is gone,
   `pytest tests/p1 -q` fails while collecting the ancestor conftest, and P1
   verifies with `pytest tests/p1 -q --confcutdir=tests/p1`. P1 does not edit it:
   it is outside P1's zone.
2. **`apps/api` still imports the v0.2 contract names.** The v0.3 surface is
   `packages.shared.models`; the v0.2 names (`DailyLog`, `RiskResponse`,
   `VoIResponse`, `QualityResponse`, ...) no longer exist and no compatibility
   layer was added, per the instruction not to keep v0.2 compatibility without a
   concrete need.

---

## Later handoffs

`H2` (golden vectors and pure facades), `H3` (caregiver journey), `H4` (corpus
and catalogue manifests) and the M5 evaluation artifacts are added to this page
as they are published.
