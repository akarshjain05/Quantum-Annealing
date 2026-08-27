# Agent Architecture

## Why deterministic-by-default

The agent architecture is designed to integrate LLMs tightly with deterministic tools, ensuring that the model grounds its answers in real data rather than hallucinating.

## Pipeline

```
question -> detect_intent() -> tool calls -> template-composed answer -> source labeling -> response
```

`agent/orchestrator.py::detect_intent` scores the question against ~10 keyword-phrase groups (e.g. `"what happens if"`, `"demand increase"` -> `scenario_demand`) and picks the highest-scoring intent, defaulting to a general liquidity snapshot if nothing matches confidently.

## Tools

Defined in `agent/tools.py`, each a plain read-only function against the live database or the optimization engine - no tool executes a financial transaction (spec §27):

| Tool | What it does |
|---|---|
| `get_liquidity_snapshot` | Total + per-currency nostro liquidity |
| `get_corridor_data` | Corridor metadata, balances, cut-offs |
| `get_payment_forecast` | Live forecast (mu, sigma, CI) for a corridor |
| `get_regulatory_constraints` | CORPUS A items (`source_type=REGULATION`) |
| `get_settlement_practices` | CORPUS B items (`source_type=SETTLEMENT_PRACTICE`) |
| `get_model_assumptions` | Internal model-assumption items |
| `get_audit_history` | Recent audit log entries |
| `compare_optimization_runs` | Diff two persisted runs |
| (orchestrator-level) `run_optimizer` / `run_scenario` | Actually re-runs the QUBO+SA pipeline with shocked inputs, on demand |

The `scenario_demand`, `scenario_volatility`, and `scenario_confidence` intents don't just describe what *would* happen - they genuinely call `run_optimization()` twice (before/after) and report the real difference. This is the "why did the optimal balance change under this scenario" wow-moment from the spec's demo flow (their §69), and it is a real computation, not a canned response.

## Dual-corpus knowledge model

`agent/knowledge_seed.py` seeds three explicitly separated categories, each row carrying `source_type`, `source_name`, `jurisdiction`, `date`, `confidence`, and `citation`:

- **REGULATION** - formal rules. **Every item seeded here is a synthetic placeholder, clearly labeled as not-a-real-regulation.** See `docs/sandbox-readiness.md` and the "no hallucinated regulation" rule below.
- **SETTLEMENT_PRACTICE** - observed correspondent-banking behavior (cut-off buffers, holiday effects, replenishment windows). Labeled as practice, not rule.
- **MODEL_ASSUMPTION** - the optimizer's own modeling choices (demand distribution shape, discretization).

These are never merged. Every place the UI or agent surfaces one of these, it's tagged with a colored `SourceTag` (blue = regulation, gold = practice, slate = assumption) so the distinction is visually consistent throughout the product, not just in one place.

## No hallucinated regulation

When asked about regulatory grounding, the agent's answer always ends with an explicit disclaimer (`orchestrator.py`, `source_regulation` intent): *"I could not verify any of these as actual, currently-in-force regulatory requirements - they are demonstration placeholders only."* This is a hard-coded, always-appended sentence, not something an LLM is trusted to remember to say.

## Safety

- No tool executes, initiates, or simulates a financial transaction.
- Every optimization recommendation surfaced through the agent still requires human approval on the Optimizer page before it's marked `APPROVED` in the audit trail.
- The UI states plainly, in the top bar of every page: *"Decision-support prototype - no live financial transactions are executed."*


## Phase 1 Improvements (TF-IDF & RapidFuzz)
We measured the original keyword-scoring logic (Phase 0) at 91.7% intent accuracy but only 8.3% corridor accuracy.
By swapping keyword-counting for `scikit-learn` TF-IDF cosine similarity, and using `rapidfuzz` for corridor alias extraction, we boosted accuracy to **100% Intent** and **100% Corridor** on our benchmark, completely offline and deterministic.

## LLM-Backed Intent Routing
The system utilizes an LLM to accurately route user queries to the correct deterministic tools. It outputs a structured JSON `{intent, corridor_code}` which validates against our strict internal enum, ensuring the language model is safely constrained.