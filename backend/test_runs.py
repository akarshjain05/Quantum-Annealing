import requests
import json
import time

API_URL = "http://localhost:8001/api/optimization/run"

def run_test():
    results = []
    print("Running optimization 4 times...")
    for i in range(4):
        seed = int(time.time()) + i * 100
        payload = {
            "random_seed": seed
        }
        resp = requests.post(API_URL, json=payload)
        if resp.status_code != 200:
            print(f"Run {i+1} failed:", resp.text)
            continue
        
        data = resp.json()
        results.append({
            "run": i + 1,
            "seed": seed,
            "initial_energy": data["initial_energy"],
            "final_energy": data["final_energy"],
            "current_liquidity_musd": data["current_liquidity_musd"],
            "optimized_liquidity_musd": data["optimized_liquidity_musd"],
            "capital_released_musd": data["capital_released_musd"],
        })
        print(f"--- Run {i+1} (seed {seed}) ---")
        print(f"Final Energy: {data['final_energy']}")
        print(f"Current Liq:  ${data['current_liquidity_musd']}M")
        print(f"Optimized:    ${data['optimized_liquidity_musd']}M")
        print(f"Released:     ${data['capital_released_musd']}M")
    
    print("\nSummary:")
    for r in results:
        print(f"Run {r['run']}: Released ${r['capital_released_musd']}M (Energy: {r['final_energy']})")

if __name__ == "__main__":
    run_test()
