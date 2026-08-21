import requests
import json
import time

API_URL = "http://localhost:8001/api/optimization/run"

def run_test():
    payload = {
        "capital_cap_musd": 250.0
    }
    resp = requests.post(API_URL, json=payload)
    if resp.status_code != 200:
        print("Failed:", resp.text)
        return
    
    data = resp.json()
    print(f"Final Energy: {data['final_energy']}")
    print(f"Optimized:    ${data['optimized_liquidity_musd']}M")
    print(f"Released:     ${data['capital_released_musd']}M")
    print(f"Variables:    {data['qubo_variables']}")
    
if __name__ == "__main__":
    run_test()
