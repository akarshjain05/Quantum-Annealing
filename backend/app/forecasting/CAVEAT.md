# Forecasting Limitations & Caveats

## Phase 4: The Synthetic Skew Reality

Our synthetic data generator is roughly symmetric by construction (Normal-ish day totals × a weekend multiplier). It does not natively exhibit meaningful mathematical skew or fat tails. 

Because of this, testing advanced Empirical Simulation VaR against our 7-day synthetic dataset yielded no improvement over a simple Gaussian parametric buffer. 

### The Honest Path Forward
We have chosen **Path (A): Deliberately inject synthetic shock events with fatter tails purely to stress-test the new machinery.** 

We wrote a standalone test (`synthetic_fat_tail_test.py`) that generates 365 days of data and artificially injects massive volume shocks into 10% of the days. The results were conclusive:
- **Gaussian Parametric Breach Rate:** 10.5% (massively under-capitalized)
- **Empirical Simulation Breach Rate:** 4.6% (perfectly calibrated to the 95% target)

**CAVEAT:** This is clearly labeled as a synthetic stress test, and is *not* evidence about real-world payment demand. The machinery correctly handles skew when it exists, but we are waiting for the real/proxy data from the earlier roadmap conversation (Tier 2, #9) before claiming this limitation is actually resolved in production.
