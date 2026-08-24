import React, { useEffect, useState } from 'react';
import client from '../api/client';
import { EmptyState, Loading } from '../components/Common';

export default function NostroAccounts() {
  const [accounts, setAccounts] = useState(null);

  useEffect(() => {
    client.get("/api/nostro")
      .then(res => setAccounts(res.data))
      .catch(err => console.error("Failed to load Nostro accounts:", err));
  }, []);

  if (!accounts) return <Loading label="Loading Nostro directory" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Nostro Accounts Directory</h1>
        <p className="text-sm text-muted mt-1">Direct API connections to correspondent banks and clearing houses.</p>
      </div>
      
      {accounts.length === 0 ? (
        <EmptyState title="No accounts found" hint="Database is empty." />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm text-left">
            <thead className="text-[11px] uppercase tracking-wide text-muted font-mono border-b border-border bg-subtle">
              <tr>
                <th className="px-4 py-3 font-medium">Account Identifier</th>
                <th className="px-4 py-3 font-medium">Correspondent</th>
                <th className="px-4 py-3 font-medium">Currency</th>
                <th className="px-4 py-3 font-medium">Balance</th>
                <th className="px-4 py-3 font-medium text-right">Status</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map(acc => (
                <tr key={acc.id} className="border-b border-border/60 hover:bg-surface/50">
                  <td className="px-4 py-3 font-mono text-teal">{acc.account_name}</td>
                  <td className="px-4 py-3">{acc.institution_name}</td>
                  <td className="px-4 py-3">{acc.currency}</td>
                  <td className="px-4 py-3 font-mono">${acc.current_balance_musd.toFixed(1)}M</td>
                  <td className="px-4 py-3 text-right"><span className="text-teal font-medium text-xs">API CONNECTED</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
