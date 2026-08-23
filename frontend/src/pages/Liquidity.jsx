import React from 'react';

export default function Liquidity() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Global Liquidity Overview</h1>
        <p className="text-sm text-muted mt-1">Aggregated view of Nostro account balances across all jurisdictions and correspondents.</p>
      </div>
      <div className="card p-8 text-center border-dashed border-border/60">
        <div className="text-muted text-sm">
          <span className="block text-primary mb-2">Detailed liquidity mapping is active in the backend.</span>
          For the current demo flow, liquidity allocation is managed directly via the <a href="/optimizer" className="underline hover:text-primary">Optimizer</a> and <a href="/corridors" className="underline hover:text-primary">Corridors</a> pages.
        </div>
      </div>
    </div>
  );
}
