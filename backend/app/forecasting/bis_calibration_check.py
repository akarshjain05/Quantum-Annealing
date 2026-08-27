"""
BIS TRIENNIAL SURVEY CALIBRATION CHECK
=======================================
Compares our synthetic corridor base volumes against real-world BIS 2022
Triennial Central Bank Survey FX turnover data to validate whether
our synthetic data generator's relative corridor ordering and rough
proportions are realistic.

Source: BIS Triennial Central Bank Survey, April 2022
       https://www.bis.org/statistics/rpfx22.htm

NOTE: BIS reports daily average turnover in USD billions, net-net basis.
      Our synthetic base_vol is daily demand in USD millions for a single
      hypothetical GIFT City bank. The absolute scales are incomparable
      (global market vs. one bank), but the RELATIVE ORDERING and
      PROPORTIONS between currency pairs should roughly match.
"""

# ========================================================================
# BIS 2022 Triennial Survey: Daily average FX turnover by currency pair
# (USD billions, net-net basis, April 2022)
# Source: Table 2, https://www.bis.org/statistics/rpfx22.htm
# ========================================================================
BIS_DAILY_TURNOVER_BN = {
    "EUR/USD": 1705,    # ~23% of $7.5T
    "USD/JPY": 1014,    # ~14%
    "USD/GBP":  714,    # ~9.5%
    "USD/CHF":  375,    # ~5%
    "EUR/GBP":  131,    # ~1.7%  (cross pair)
    "USD/INR":  120,    # ~1.6%
    "EUR/INR":   12,    # ~0.16% (estimated from EME cross data)
    "SGD/INR":    3,    # ~0.04% (estimated — very small cross)
    "AED/INR":    5,    # ~0.07% (estimated — very small cross)
    "JPY/INR":    2,    # ~0.03% (estimated — very small cross)
}

# ========================================================================
# Our synthetic generator's base_vol ($M/day for a single bank)
# Extracted from seed_data.py CORRIDORS constant
# ========================================================================
SYNTHETIC_BASE_VOL = {
    "USD_EUR":  6.0,
    "EUR_USD":  5.8,
    "USD_GBP":  3.0,
    "USD_CHF":  1.8,
    "GBP_EUR":  2.0,
    "USD_INR":  4.5,
    "EUR_INR":  2.2,
    "SGD_INR":  1.1,
    "AED_INR":  1.5,
    "JPY_INR":  0.8,
    "GBP_INR":  0.9,
}

# Map our corridor codes to BIS pair names
CORRIDOR_TO_BIS = {
    "USD_EUR":  "EUR/USD",
    "EUR_USD":  "EUR/USD",
    "USD_GBP":  "USD/GBP",
    "USD_CHF":  "USD/CHF",
    "GBP_EUR":  "EUR/GBP",
    "USD_INR":  "USD/INR",
    "EUR_INR":  "EUR/INR",
    "SGD_INR":  "SGD/INR",
    "AED_INR":  "AED/INR",
    "JPY_INR":  "JPY/INR",
    "GBP_INR":  "USD/INR",  # No direct BIS pair; proxy via USD/INR (INR crosses)
}


def run_calibration():
    # Normalize both to relative shares (% of largest)
    # BIS: normalize to EUR/USD (the largest)
    bis_max = max(BIS_DAILY_TURNOVER_BN.values())
    bis_relative = {k: round(v / bis_max * 100, 1) for k, v in BIS_DAILY_TURNOVER_BN.items()}
    
    # Synthetic: normalize to USD_EUR + EUR_USD combined (the largest)
    synth_max = max(SYNTHETIC_BASE_VOL.values())
    synth_relative = {k: round(v / synth_max * 100, 1) for k, v in SYNTHETIC_BASE_VOL.items()}
    
    print("=" * 80)
    print("BIS TRIENNIAL SURVEY vs SYNTHETIC DATA: CALIBRATION CHECK")
    print("=" * 80)
    print(f"\n{'Our Corridor':<14} | {'base_vol':<10} | {'Synth %':<10} | {'BIS Pair':<10} | {'BIS $Bn':<10} | {'BIS %':<10} | {'Match?'}")
    print("-" * 80)
    
    mismatches = []
    
    # Sort by synthetic base_vol descending
    for code in sorted(SYNTHETIC_BASE_VOL.keys(), key=lambda k: SYNTHETIC_BASE_VOL[k], reverse=True):
        vol = SYNTHETIC_BASE_VOL[code]
        s_pct = synth_relative[code]
        
        bis_pair = CORRIDOR_TO_BIS.get(code, "N/A")
        bis_bn = BIS_DAILY_TURNOVER_BN.get(bis_pair, 0)
        b_pct = bis_relative.get(bis_pair, 0)
        
        # A "match" means within same order-of-magnitude tier
        # Tier 1: >50% (mega pairs like EUR/USD)
        # Tier 2: 10-50% (large pairs like USD/GBP, USD/CHF)
        # Tier 3: 1-10% (medium pairs like USD/INR, EUR/GBP)
        # Tier 4: <1% (small crosses like SGD/INR, AED/INR)
        def tier(pct):
            if pct > 50: return "MEGA"
            if pct > 10: return "LARGE"
            if pct > 1: return "MEDIUM"
            return "SMALL"
        
        s_tier = tier(s_pct)
        b_tier = tier(b_pct)
        match = "✓" if s_tier == b_tier else "✗ MISMATCH"
        
        if s_tier != b_tier:
            mismatches.append((code, s_tier, b_tier))
        
        print(f"{code:<14} | ${vol:<9} | {s_pct:<10} | {bis_pair:<10} | ${bis_bn:<9} | {b_pct:<10} | {match}")
    
    print("\n" + "=" * 80)
    print("FINDINGS:")
    print("=" * 80)
    
    if not mismatches:
        print("All corridors match BIS relative ordering. Synthetic data is well-calibrated.")
    else:
        print(f"\n{len(mismatches)} MISMATCHES FOUND:\n")
        for code, s_tier, b_tier in mismatches:
            bis_pair = CORRIDOR_TO_BIS[code]
            print(f"  {code}: Synthetic tier={s_tier}, BIS tier={b_tier}")
            print(f"    -> Our generator treats {code} as {s_tier}, but BIS says {bis_pair} is {b_tier}")
            
            # Suggest a fix
            bis_bn = BIS_DAILY_TURNOVER_BN.get(bis_pair, 0)
            bis_ratio = bis_bn / bis_max
            suggested_vol = round(bis_ratio * 6.0, 1)  # Scale to our largest (USD_EUR = 6.0)
            print(f"    -> Suggested base_vol correction: ${suggested_vol}M (from ${SYNTHETIC_BASE_VOL[code]}M)")
        
        print("\nCAVEAT: BIS data is global FX turnover. Our model represents a single")
        print("GIFT City bank's Nostro flows, which would naturally overweight INR crosses")
        print("relative to global averages. Some mismatches are EXPECTED and DEFENSIBLE.")
        print("The key validation is that USD_EUR >> USD_GBP >> USD_CHF ordering holds.")


if __name__ == "__main__":
    run_calibration()
