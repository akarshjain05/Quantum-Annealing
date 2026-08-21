# Demo Script (~5 minutes)

Numbers below are illustrative of the *shape* of the result, drawn from a real run during this build (see README). Your live run will produce its own real numbers from the same real computation - read those off the screen rather than these.

## Step 1 - Dashboard (30s)
Open `/`. Point at the total nostro liquidity figure and the settlement-window timeline.
> "Demo Global Bank pre-funds 11 corridors across 8 currencies. This timeline shows every corridor's settlement window and cut-off across a 24-hour UTC day - cross-border liquidity isn't just about how much you hold, it's about when it needs to be there."

## Step 2 - Corridors (30s)
Open `/corridors`. Click a row (e.g. USD_INR) to expand its live forecast.
> "Each corridor has real synthetic transaction history behind it - 90 days, several thousand transactions. This forecast panel is computed live from that history, not hardcoded."

## Step 3 - Optimizer (90s)
Open `/optimizer`. Walk through the inputs, then click **Run optimization**.
> "We formulate liquidity allocation as a QUBO - a quadratic binary optimization problem - and solve it with simulated annealing."
Let the staged status run (Building QUBO -> Running simulated annealing -> Refining -> Validating). When results land, point at:
- Current vs. optimized liquidity and capital released
- The convergence chart (energy actually decreasing over iterations)
- Constraint satisfaction / any flagged violations
- Expand one corridor's "why?" to show the structured explanation and the baseline comparison (static / rule-based / greedy / quantum-inspired)

> "Notice this isn't just 'reduce everything' - if a corridor's current balance is actually below the safety requirement, the model recommends increasing it. That's a real per-corridor optimization, not a blanket haircut."

## Step 4 - QUBO Inspector (45s)
Open `/qubo`. Show the heatmap and variable count.
> "This is the actual formulation for the run we just did - the real Q matrix, not a mockup. Today's solver is simulated annealing; the formulation itself is quantum-ready - the same matrix is the input format a quantum annealer would need."

## Step 5 - Agent (60s)
Open `/agent`. Ask, live:
- *"Why are we holding too much USD liquidity?"* - watch it call `get_liquidity_snapshot` + `run_optimizer` and answer with real numbers.
- *"What happens if USD_INR demand increases by 30%?"* - watch it re-run the optimizer before/after and explain the shift in required vs. recommended liquidity.
- *"Which recommendation is based on a regulatory rule?"* - watch it explicitly say it cannot verify any seeded item as a real regulation (all synthetic placeholders), demonstrating the "no hallucinated regulation" rule live.

> "Zero LLM API key is configured anywhere in this environment. Every one of these answers is a deterministic tool call against the live database and the real optimizer - not a language model guessing."

## Step 6 - Stress Tests (30s)
Open `/stress-tests`, run the battery.
> "Eight predefined shocks - demand up, volatility up, confidence tightened to 99.9%, a combined holiday-style shock - each one a genuine re-optimization, not a lookup table."

## Step 7 - Scenarios (30s)
Open `/scenarios`, pick a corridor, push the demand slider, run it.
> "This is the same underlying engine, exposed as an interactive what-if tool."

## Step 8 - Audit Trail (30s)
Open `/audit`. Point at the hash chain and the "chain valid" badge.
> "Every run and every human approval is appended to a SHA-256 hash chain - tamper-evident, not a blockchain, but the same core idea: if anyone edits history, the chain breaks from that point forward, and we can prove it - this endpoint actually recomputes and checks every hash."

## Step 9 - Close
> "Today: classical simulated annealing solving a real QUBO. Tomorrow: the same formulation, portable to quantum annealing hardware as it matures. In between: an agentic layer that keeps regulation, observed practice, and model assumptions honestly separated, a validator that never trusts the solver blindly, and a full audit trail - built with GIFT City's IFSC ecosystem in mind. See `docs/sandbox-readiness.md` for how we'd approach sandbox evaluation."
