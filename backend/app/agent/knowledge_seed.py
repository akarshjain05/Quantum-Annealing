"""
Seed content for the dual-corpus knowledge base (spec §12-13, §47).

IMPORTANT: every REGULATION-tagged item below is SYNTHETIC and clearly
labeled as such (is_synthetic=True). None of this is a substitute for
actual IFSCA/RBI regulatory text, and the system never claims otherwise
(see docs/sandbox-readiness.md and the "No Hallucinated Regulation" rule).
Real deployments must replace CORPUS A with actual ingested regulatory
source documents, cited to their official publication.
"""

KNOWLEDGE_ITEMS = [
    # --- CORPUS A: formal regulatory / policy knowledge (SYNTHETIC PLACEHOLDER TEXT) ---
    {
        "source_type": "REGULATION",
        "title": "Illustrative minimum liquidity coverage principle",
        "content": (
            "Synthetic placeholder representing the general category of prudential liquidity "
            "coverage requirements that apply to regulated banking entities. A production "
            "deployment must replace this with the actual cited text of applicable IFSCA/RBI/"
            "central-bank rules for the relevant jurisdiction and license category."
        ),
        "source_name": "SYNTHETIC-DEMO-REG-001 (not an actual regulation)",
        "source_date": "",
        "jurisdiction": "Illustrative / not jurisdiction-specific",
        "confidence": 0.0,
        "citation": "None - synthetic placeholder only",
        "is_synthetic": True,
    },
    {
        "source_type": "REGULATION",
        "title": "Illustrative reporting/audit obligation",
        "content": (
            "Synthetic placeholder representing the general category of requirements that "
            "material treasury/liquidity decisions be logged and auditable. Replace with actual "
            "cited regulatory text before any real deployment."
        ),
        "source_name": "SYNTHETIC-DEMO-REG-002 (not an actual regulation)",
        "source_date": "",
        "jurisdiction": "Illustrative / not jurisdiction-specific",
        "confidence": 0.0,
        "citation": "None - synthetic placeholder only",
        "is_synthetic": True,
    },
    # --- CORPUS B: settlement / operational practice ---
    {
        "source_type": "SETTLEMENT_PRACTICE",
        "title": "Correspondent cut-off buffer convention",
        "content": (
            "Observed market practice: correspondent banks commonly require nostro pre-funding "
            "confirmation 1-2 hours ahead of the published cut-off time to allow for confirmation "
            "and exception handling, rather than exactly at the nominal cut-off."
        ),
        "source_name": "Synthetic demo corpus - illustrative market practice",
        "source_date": "2026",
        "jurisdiction": "Cross-border correspondent banking (general)",
        "confidence": 0.7,
        "citation": "Internal synthetic demo dataset",
        "is_synthetic": True,
    },
    {
        "source_type": "SETTLEMENT_PRACTICE",
        "title": "Holiday-adjacent liquidity build-up",
        "content": (
            "Observed pattern: corridors into markets with an upcoming currency holiday tend to "
            "see elevated payment volume in the 1-2 business days prior, as counterparties settle "
            "ahead of the closure."
        ),
        "source_name": "Synthetic demo corpus - illustrative market practice",
        "source_date": "2026",
        "jurisdiction": "Cross-border correspondent banking (general)",
        "confidence": 0.65,
        "citation": "Internal synthetic demo dataset",
        "is_synthetic": True,
    },
    {
        "source_type": "SETTLEMENT_PRACTICE",
        "title": "Same-day replenishment window",
        "content": (
            "Observed practice: for corridors with settlement windows spanning multiple UTC time "
            "buckets, treasury desks can typically replenish a nostro account intraday if a "
            "shortfall is detected early enough in the settlement window."
        ),
        "source_name": "Synthetic demo corpus - illustrative market practice",
        "source_date": "2026",
        "jurisdiction": "Cross-border correspondent banking (general)",
        "confidence": 0.6,
        "citation": "Internal synthetic demo dataset",
        "is_synthetic": True,
    },
    # --- Model assumptions ---
    {
        "source_type": "MODEL_ASSUMPTION",
        "title": "Demand distribution assumption",
        "content": (
            "The optimizer assumes corridor payment demand over the forecast horizon is "
            "approximately normally distributed, characterized by its mean and standard "
            "deviation estimated from trailing transaction history. Real demand may be "
            "skewed or fat-tailed, particularly around holidays or market stress."
        ),
        "source_name": "NostroQ model documentation",
        "source_date": "2026",
        "jurisdiction": "N/A",
        "confidence": 0.5,
        "citation": "docs/qubo-mathematics.md",
        "is_synthetic": True,
    },
    {
        "source_type": "MODEL_ASSUMPTION",
        "title": "Liquidity discretization assumption",
        "content": (
            "Liquidity levels are restricted to a fixed set of discrete buckets "
            "($0/1/2/5/10/20/50/100M) for QUBO tractability. The true optimum may lie "
            "between buckets; finer discretization trades solution precision for a larger "
            "QUBO and longer solve time."
        ),
        "source_name": "NostroQ model documentation",
        "source_date": "2026",
        "jurisdiction": "N/A",
        "confidence": 0.9,
        "citation": "docs/qubo-mathematics.md",
        "is_synthetic": True,
    },
]
