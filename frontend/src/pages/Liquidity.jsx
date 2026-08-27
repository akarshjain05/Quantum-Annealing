import React, { useEffect, useState } from 'react';
import client from '../api/client';
import { EmptyState, Loading } from '../components/Common';

export default function Liquidity() {
  const [accounts, setAccounts] = useState(null);

  useEffect(() => {
    client.get("/api/nostro")
      .then(res => setAccounts(res.data))
      .catch(err => console.error("Failed to load Nostro accounts:", err));
  }, []);

  if (!accounts) return <Loading label="Loading liquidity data" />;

  const byCurrency = accounts.reduce((acc, a) => {
    acc[a.currency] = (acc[a.currency] || 0) + a.current_balance_musd;
    return acc;
  }, {});

  const total = Object.values(byCurrency).reduce((sum, v) => sum + v, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Global Liquidity Overview</h1>
        <p className="text-sm text-muted mt-1">Aggregated view of Nostro account balances across all jurisdictions and correspondents.</p>
      </div>
      
      {accounts.length === 0 ? (
        <EmptyState title="No Liquidity Data" hint="No accounts configured." />
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="card p-5">
              <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-1">Total Global Liquidity</div>
              <div className="text-3xl font-display text-primary">${total.toFixed(1)}M</div>
            </div>
          </div>
          
          <div className="card overflow-hidden">
            <table className="w-full text-sm text-left">
              <thead className="text-[11px] uppercase tracking-wide text-muted font-mono border-b border-border bg-subtle">
                <tr>
                  <th className="px-4 py-3 font-medium">Currency</th>
                  <th className="px-4 py-3 font-medium">Total Balance (MUSD Equivalent)</th>
                  <th className="px-4 py-3 font-medium text-right">Share</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(byCurrency)
                  .sort((a, b) => b[1] - a[1])
                  .map(([currency, amount]) => (
                  <tr key={currency} className="border-b border-border/60 hover:bg-surface/50">
                    <td className="px-4 py-3 font-mono text-teal">{currency}</td>
                    <td className="px-4 py-3 font-mono">${amount.toFixed(1)}M</td>
                    <td className="px-4 py-3 text-right text-muted">{((amount / total) * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
