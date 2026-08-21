# Pitch Story

Cross-border payments move money globally, but liquidity often has to move *before* the payment does.

Every corridor requires confidence that settlement liquidity will be available - across time zones, cut-off windows, and holidays a bank doesn't control.

That's a capital allocation problem, and today it's mostly solved with static buffers: hold more than you'll probably need, because the cost of being wrong is worse than the cost of sitting on idle capital.

We turn that problem into a QUBO - a quadratic binary optimization over which discrete liquidity level each corridor should hold.

We solve it today using simulated annealing, built from scratch, tested against brute-force energy recomputation, and honest about a real bug we found and fixed in our own solver along the way.

We built the architecture so the same formulation can migrate toward quantum annealing as that hardware matures - not as a claim we're using it today, but as a genuine property of how the QUBO is constructed.

Our agentic layer adds the context a static buffer can't: what's regulation, what's just how correspondent banks tend to behave, and what's our own model's assumption - three things treasury teams currently have to keep straight in their heads, that we keep straight in the data model instead.

The result isn't just a prediction. It's an explainable liquidity allocation recommendation, validated independently of the solver that produced it, that a human has to approve before anything downstream would ever act on it.

In one real run during this build: $386.06M in nostro liquidity, optimized down to $300.00M - $86.06M released, about 22% capital efficiency - without materially increasing modeled settlement risk, and with one corridor correctly flagged to *increase* rather than blindly shrink everything. That's not a target we hit; it's what the model actually produced.
