import React from 'react';

export default function NostroAccounts() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Nostro Accounts Directory</h1>
        <p className="text-sm text-muted mt-1">Direct API connections to correspondent banks and clearing houses.</p>
      </div>
      <div className="card overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="text-[11px] uppercase tracking-wide text-muted font-mono border-b border-border bg-subtle">
            <tr>
              <th className="px-4 py-3 font-medium">Account Identifier</th>
              <th className="px-4 py-3 font-medium">Correspondent</th>
              <th className="px-4 py-3 font-medium">Currency</th>
              <th className="px-4 py-3 font-medium text-right">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-border/60">
              <td className="px-4 py-3 font-mono">NY-JPM-USD-001</td>
              <td className="px-4 py-3">JPMorgan Chase NY</td>
              <td className="px-4 py-3">USD</td>
              <td className="px-4 py-3 text-right"><span className="text-teal font-medium">API Connected</span></td>
            </tr>
            <tr className="border-b border-border/60">
              <td className="px-4 py-3 font-mono">LDN-BAR-GBP-002</td>
              <td className="px-4 py-3">Barclays London</td>
              <td className="px-4 py-3">GBP</td>
              <td className="px-4 py-3 text-right"><span className="text-teal font-medium">API Connected</span></td>
            </tr>
            <tr>
              <td className="px-4 py-3 font-mono">FRA-DB-EUR-003</td>
              <td className="px-4 py-3">Deutsche Bank Frankfurt</td>
              <td className="px-4 py-3">EUR</td>
              <td className="px-4 py-3 text-right"><span className="text-teal font-medium">API Connected</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
