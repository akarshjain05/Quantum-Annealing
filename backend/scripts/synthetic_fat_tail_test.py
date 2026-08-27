import numpy as np

def run_fat_tail_stress_test(days=365, confidence_level=0.95):
    """
    PATH (A): SYNTHETIC SHOCK STRESS TEST
    Generates a 365-day synthetic dataset with deliberate fat tails (shocks)
    to prove that the Empirical Quantile VaR machinery correctly handles 
    non-Gaussian distributions better than a parametric Gaussian assumption.
    
    Disclaimer: This is purely a synthetic stress test to validate the mathematics 
    of the model, NOT evidence about real-world Nostro payment demand.
    """
    np.random.seed(42)
    
    # Generate 365 days of "normal" demand (mean 100, std 15)
    base_demand = np.random.normal(100, 15, days)
    
    # Inject "Fat Tails" (10% chance of a massive 3x-5x shock)
    shocks = np.random.uniform(3, 5, days) * 100
    is_shock = np.random.random(days) < 0.10
    
    actual_demand = base_demand + (shocks * is_shock)
    
    # Rolling origin backtest
    z_score = 1.96 if confidence_level == 0.95 else 1.645
    
    g_breaches = 0
    e_breaches = 0
    total_windows = 0
    
    # We need a decent lookback to compute empirical quantiles (e.g., 60 days)
    lookback = 60
    
    for t in range(lookback, days):
        history = actual_demand[:t]
        actual_t = actual_demand[t]
        
        # Simple forecasting model for the test: Moving Average
        mu = np.mean(history[-14:]) # 14 day MA
        sigma = np.std(history[-30:]) # 30 day volatility
        
        # 1. Gaussian Parametric
        ci_high_gaussian = mu + z_score * sigma
        if actual_t > ci_high_gaussian:
            g_breaches += 1
            
        # 2. Empirical VaR
        # Build residuals for the past 60 days
        residuals = []
        for past_t in range(14, t):
            past_hist = actual_demand[:past_t]
            past_mu = np.mean(past_hist[-14:])
            residuals.append(actual_demand[past_t] - past_mu)
            
        emp_margin = float(np.quantile(residuals, confidence_level))
        ci_high_empirical = mu + max(0, emp_margin)
        
        if actual_t > ci_high_empirical:
            e_breaches += 1
            
        total_windows += 1
        
    print("==========================================================")
    print("PHASE 4: SYNTHETIC FAT-TAIL STRESS TEST (Path A)")
    print("==========================================================")
    print(f"Total simulated days: {days}")
    print(f"Windows tested: {total_windows}")
    print(f"Target Confidence Level: {confidence_level*100:.1f}% (Expected Breach: {(1-confidence_level)*100:.1f}%)")
    print("-" * 58)
    
    g_rate = g_breaches / total_windows
    e_rate = e_breaches / total_windows
    
    print(f"Gaussian Parametric Breach Rate: {g_rate:.1%} (Breaches: {g_breaches})")
    print(f"Empirical Simulation Breach Rate: {e_rate:.1%} (Breaches: {e_breaches})")
    print("-" * 58)
    
    if abs(e_rate - 0.05) < abs(g_rate - 0.05):
        print("=> SUCCESS: Empirical VaR is significantly better calibrated to fat tails!")
    else:
        print("=> FAILURE: Empirical VaR did not improve calibration.")

if __name__ == "__main__":
    run_fat_tail_stress_test()
