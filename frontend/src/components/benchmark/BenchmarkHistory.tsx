// frontend/src/components/benchmark/BenchmarkHistory.tsx
/**
 * Benchmark History Component
 * 
 * Shows list of past benchmark runs with key metrics.
 */

import React from 'react';
import { formatDistanceToNow } from 'date-fns';

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

interface BenchmarkHistoryProps {
  runs: BenchmarkHistoryItem[];
  onSelectRun?: (runId: string) => void;
  selectedRunId?: string;
  loading?: boolean;
}

const formatTime = (ms: number): string => {
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
};

const formatMoney = (amount: number): string => {
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
  if (amount >= 1_000) return `$${(amount / 1_000).toFixed(0)}K`;
  return `$${amount.toFixed(0)}`;
};

const getSolverDisplayName = (solver: string): string => {
  const names: Record<string, string> = {
    'classical_sa_numpy': 'Classical SA',
    'dwave_neal_sa': 'D-Wave Neal',
    'qaoa_custom': 'QAOA',
    'qiskit_qaoa': 'Qiskit QAOA'
  };
  return names[solver] || solver;
};

export const BenchmarkHistory: React.FC<BenchmarkHistoryProps> = ({
  runs,
  onSelectRun,
  selectedRunId,
  loading = false
}) => {
  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <div className="p-4 border-b border-gray-700">
          <div className="h-5 bg-gray-700 rounded w-1/3 animate-pulse"></div>
        </div>
        <div className="divide-y divide-gray-700">
          {[1, 2, 3].map(i => (
            <div key={i} className="p-4 animate-pulse">
              <div className="h-4 bg-gray-700 rounded w-1/2 mb-2"></div>
              <div className="h-3 bg-gray-700 rounded w-1/3"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-8 text-center">
        <p className="text-gray-400">No benchmark history available</p>
        <p className="text-sm text-gray-500 mt-2">
          Run an optimization with benchmark enabled to see results here.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <div className="p-4 border-b border-gray-700">
        <h3 className="font-medium text-white">Benchmark History</h3>
        <p className="text-sm text-gray-400">{runs.length} runs</p>
      </div>
      
      <div className="divide-y divide-gray-700 max-h-96 overflow-y-auto">
        {runs.map(run => (
          <button
            key={run.run_id}
            onClick={() => onSelectRun?.(run.run_id)}
            className={`w-full p-4 text-left transition-colors ${
              selectedRunId === run.run_id
                ? 'bg-teal-500/10 border-l-2 border-teal-500'
                : 'hover:bg-gray-700/50'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-sm text-gray-400">
                {run.run_id.slice(0, 20)}...
              </span>
              <span className="text-xs text-gray-500">
                {formatDistanceToNow(new Date(run.timestamp), { addSuffix: true })}
              </span>
            </div>
            
            <div className="grid grid-cols-3 gap-2 text-sm">
              <div>
                <span className="text-gray-500">Size:</span>{' '}
                <span className="text-white">{run.problem_size} vars</span>
              </div>
              <div>
                <span className="text-gray-500">Best:</span>{' '}
                <span className="text-teal-400">
                  {getSolverDisplayName(run.best_solver)}
                </span>
              </div>
              <div>
                <span className="text-gray-500">Time:</span>{' '}
                <span className="text-white">{formatTime(run.total_time_ms)}</span>
              </div>
            </div>
            
            {run.capital_released && (
              <div className="mt-2 text-sm">
                <span className="text-gray-500">Capital Released:</span>{' '}
                <span className="text-green-400">{formatMoney(run.capital_released)}</span>
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
};

export default BenchmarkHistory;
