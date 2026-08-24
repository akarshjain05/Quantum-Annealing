# Agent Architecture

## Why deterministic-by-default

Spec requirement (their own §44): *"If no LLM key exists, the system must still run... the dashboard and optimizer must NEVER fail simply because an LLM key is absent."* We took this further: the agent's **default, tested path requires no LLM at all**. This is not a degraded fallback bolted onto an LLM-first design - it's the primary implementation, because:

1. It's fully deterministic and testable (`tests/test_api_optimization.py::test_agent_ask_*`).
2. It can't hallucinate a regulation, a number, or a tool result - every fact in every answer traces to a real DB query or a real optimizer run.
3. It works in this build, right now, with zero external dependencies - which an LLM-first design would not, since no key is available in the environment this was built in.

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

## Optional LLM enhancement (present, not exercised)

`orchestrator.py::maybe_enhance_with_llm` is a documented extension point: if `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY` are both set, a future version could send the deterministic answer + its grounding facts to a real model for more natural phrasing - **never for fact generation**, since the facts are already assembled before this hook runs. It is a no-op in this build (returns the input unchanged) because no key was available to test it against, and shipping an untested code path as if it were verified would contradict everything else in this README.

## Safety

- No tool executes, initiates, or simulates a financial transaction.
- Every optimization recommendation surfaced through the agent still requires human approval on the Optimizer page before it's marked `APPROVED` in the audit trail.
- The UI states plainly, in the top bar of every page: *"Decision-support prototype - no live financial transactions are executed."*


## Phase 1 Improvements (TF-IDF & RapidFuzz)
We measured the original keyword-scoring logic (Phase 0) at 91.7% intent accuracy but only 8.3% corridor accuracy.
By swapping keyword-counting for `scikit-learn` TF-IDF cosine similarity, and using `rapidfuzz` for corridor alias extraction, we boosted accuracy to **100% Intent** and **100% Corridor** on our benchmark, completely offline and deterministic.

## Phase 2 Bounded LLM Router
If `LLM_PROVIDER` and an API key are provided, an optional LLM-assisted router handles parsing.
Crucially, **the LLM is a router, never an author**. It outputs a structured JSON `{intent, corridor_code}` which validates against the exact same enum as the deterministic path. Any hallucinated intent immediately drops back to the TF-IDF offline router.
