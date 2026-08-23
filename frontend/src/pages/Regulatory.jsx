import React from 'react';

export default function Regulatory() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Regulatory Intelligence</h1>
        <p className="text-sm text-muted mt-1">Dual-corpus knowledge base for compliance and operational practices.</p>
      </div>
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-4">
          <span className="bg-blue-500/20 text-blue-400 text-[10px] uppercase font-bold px-1.5 py-0.5 rounded">Regulation</span>
          <span className="text-sm font-medium">Basel III LCR Constraints (Synthetic)</span>
        </div>
        <p className="text-sm text-muted">Placeholder for formal regulatory mapping. The agent uses this corpus to verify binding constraints without hallucination.</p>
      </div>
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-4">
          <span className="bg-amber-500/20 text-amber-400 text-[10px] uppercase font-bold px-1.5 py-0.5 rounded">Settlement Practice</span>
          <span className="text-sm font-medium">Intraday Cut-off Buffers</span>
        </div>
        <p className="text-sm text-muted">Operational heuristics derived from correspondent bank behavior (e.g. earlier cut-offs reducing replenishment capability).</p>
      </div>
    </div>
  );
}
