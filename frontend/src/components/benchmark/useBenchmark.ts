// frontend/src/components/benchmark/useBenchmark.ts
/**
 * React hooks for benchmark data fetching
 */

import { useState, useEffect, useCallback } from 'react';
import type { BenchmarkData } from './BenchmarkChart';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// =============================================================================
// TYPES
// =============================================================================

interface QuantumStatus {
  qiskit_available: boolean;
  qiskit_version?: string;
  dwave_available: boolean;
  neal_available: boolean;
  quantum_ready: boolean;
  available_solvers: Array<{
    type: string;
    display_name: string;
    category: string;
    is_available: boolean;
    max_variables?: number;
  }>;
  message: string;
}

interface OptimizationRequest {
  risk_config?: {
    risk_appetite?: string;
    confidence_level?: number;
    safety_buffer?: number;
  };
  solver_config?: {
    run_classical?: boolean;
    run_quantum?: boolean;
    seed?: number;
  };
  run_benchmark?: boolean;
  save_results?: boolean;
}

interface OptimizationResponse {
  run_id: string;
  timestamp: string;
  status: string;
  problem_size: number;
  num_corridors: number;
  total_liquidity: number;
  capital_released: number;
  capital_release_percent: number;
  annual_savings_opportunity: number;
  benchmark?: BenchmarkData;
  corridor_results: any[];
  qubo_info: any;
  audit_hash: string;
  configuration: any;
  warnings: string[];
}

interface BenchmarkHistoryItem {
  run_id: string;
  timestamp: string;
  problem_size: number;
  best_solver: string;
  best_energy: number;
  num_solvers_run: number;
  total_time_ms: number;
  capital_released?: number;
}

// =============================================================================
// HOOKS
// =============================================================================

/**
 * Hook for fetching quantum solver status
 */
export function useQuantumStatus() {
  const [status, setStatus] = useState<QuantumStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/api/quantum/status`);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  return { status, loading, error, refetch: fetchStatus };
}

/**
 * Hook for running optimization with benchmark
 */
export function useBenchmark() {
  const [result, setResult] = useState<OptimizationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runOptimization = useCallback(async (request: OptimizationRequest = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE}/api/quantum/optimize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          run_benchmark: true,
          save_results: true,
          ...request
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      
      const data = await response.json();
      setResult(data);
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Optimization failed';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const runQuickBenchmark = useCallback(async (
    numVariables: number = 16,
    seed: number = 42,
    runQuantum: boolean = true
  ) => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        num_variables: numVariables.toString(),
        seed: seed.toString(),
        run_quantum: runQuantum.toString()
      });
      
      const response = await fetch(
        `${API_BASE}/api/quantum/benchmark/quick?${params}`,
        { method: 'POST' }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Benchmark failed';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    result,
    loading,
    error,
    runOptimization,
    runQuickBenchmark,
    clearResult: () => setResult(null),
    clearError: () => setError(null)
  };
}

/**
 * Hook for fetching benchmark history
 */
export function useBenchmarkHistory(limit: number = 20) {
  const [history, setHistory] = useState<BenchmarkHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `${API_BASE}/api/quantum/benchmark/history?limit=${limit}`
      );
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      setHistory(data.runs || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch history');
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return { history, loading, error, refetch: fetchHistory };
}

/**
 * Hook for fetching a specific benchmark result
 */
export function useBenchmarkResult(runId: string | null) {
  const [result, setResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) {
      setResult(null);
      return;
    }

    const fetchResult = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(
          `${API_BASE}/api/quantum/benchmark/${runId}`
        );
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        setResult(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch result');
      } finally {
        setLoading(false);
      }
    };

    fetchResult();
  }, [runId]);

  return { result, loading, error };
}

export default useBenchmark;
