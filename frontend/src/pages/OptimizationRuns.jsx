import React, { useEffect, useState } from 'react';
import client from '../api/client';
import { EmptyState, Loading } from '../components/Common';

export default function OptimizationRuns() {
  const [runs, setRuns] = useState(null);

  useEffect(() => {
    client.get("/api/optimization/runs")
      .then(res => setRuns(res.data))
      .catch(err => console.error("Failed to load optimization runs:", err));
  }, []);

  if (!runs) return <Loading label="Loading optimization history" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Optimization Run History</h1>
        <p className="text-sm text-muted mt-1">Audit log of all executed QUBO formulations and solver results.</p>
      </div>
      
      {runs.length === 0 ? (
        <EmptyState title="No runs found" hint="Go to the Optimizer page to run a new optimization." />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="text-[11px] uppercase tracking-wide text-muted font-mono border-b border-border bg-subtle">
              <tr>
                <th className="px-4 py-3 font-medium">Run ID</th>
                <th className="px-4 py-3 font-medium">Timestamp</th>
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">Capital Released</th>
                <th className="px-4 py-3 font-medium text-right">Status</th>
              </tr>
            </thead>
            <tbody>
              {runs.map(run => (
                <tr key={run.run_id} className="border-b border-border/60">
                  <td className="px-4 py-3 font-mono text-xs">#{run.run_id}</td>
                  <td className="px-4 py-3 text-muted">{new Date(run.created_at).toLocaleString()}</td>
                  <td className="px-4 py-3">{run.run_type}</td>
                  <td className="px-4 py-3 font-mono">${run.capital_released_musd.toFixed(1)}M</td>
                  <td className="px-4 py-3 text-right">
                    <span className={run.status === "OPTIMAL" ? "text-teal font-medium" : "text-gold font-medium"}>
                      {run.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
