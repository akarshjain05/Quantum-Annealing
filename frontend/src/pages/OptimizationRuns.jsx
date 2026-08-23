import React from 'react';

export default function OptimizationRuns() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Optimization Run History</h1>
        <p className="text-sm text-muted mt-1">Audit log of all executed QUBO formulations and QPU solver results.</p>
      </div>
      <div className="card overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="text-[11px] uppercase tracking-wide text-muted font-mono border-b border-border bg-subtle">
            <tr>
              <th className="px-4 py-3 font-medium">Run ID</th>
              <th className="px-4 py-3 font-medium">Timestamp</th>
              <th className="px-4 py-3 font-medium">Solver</th>
              <th className="px-4 py-3 font-medium">Variables</th>
              <th className="px-4 py-3 font-medium text-right">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-border/60">
              <td className="px-4 py-3 font-mono text-xs">run_20260823_1922</td>
              <td className="px-4 py-3 text-muted">Just now</td>
              <td className="px-4 py-3">Simulated Annealing</td>
              <td className="px-4 py-3 font-mono">88</td>
              <td className="px-4 py-3 text-right"><span className="text-teal font-medium">Optimal</span></td>
            </tr>
            <tr className="border-b border-border/60">
              <td className="px-4 py-3 font-mono text-xs">run_20260823_1801</td>
              <td className="px-4 py-3 text-muted">1 hour ago</td>
              <td className="px-4 py-3">Simulated Annealing</td>
              <td className="px-4 py-3 font-mono">88</td>
              <td className="px-4 py-3 text-right"><span className="text-teal font-medium">Optimal</span></td>
            </tr>
            <tr>
              <td className="px-4 py-3 font-mono text-xs">run_20260822_0914</td>
              <td className="px-4 py-3 text-muted">Yesterday</td>
              <td className="px-4 py-3">D-Wave QPU (Simulated)</td>
              <td className="px-4 py-3 font-mono">88</td>
              <td className="px-4 py-3 text-right"><span className="text-teal font-medium">Optimal</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
