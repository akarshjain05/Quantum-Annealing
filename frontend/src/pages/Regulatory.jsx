import React, { useEffect, useState } from 'react';
import client from '../api/client';
import { EmptyState, Loading } from '../components/Common';

export default function Regulatory() {
  const [knowledge, setKnowledge] = useState(null);

  useEffect(() => {
    client.get("/api/agent/knowledge")
      .then(res => setKnowledge(res.data))
      .catch(err => console.error("Failed to fetch knowledge base", err));
  }, []);

  if (!knowledge) return <Loading label="Loading regulatory intelligence" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Regulatory Intelligence</h1>
        <p className="text-sm text-muted mt-1">Dual-corpus knowledge base for compliance and operational practices.</p>
      </div>
      
      {knowledge.length === 0 ? (
        <EmptyState title="No Knowledge Items" hint="Knowledge base is empty." />
      ) : (
        <div className="grid gap-4">
          {knowledge.map(item => (
            <div key={item.id} className="card p-6">
              <div className="flex items-center gap-3 mb-4">
                <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                  item.source_type === 'REGULATION' ? 'bg-blue-500/20 text-blue-400' : 'bg-amber-500/20 text-amber-400'
                }`}>
                  {item.source_type}
                </span>
                <span className="text-sm font-medium">{item.title}</span>
                {item.is_synthetic && (
                  <span className="ml-auto text-[9px] uppercase tracking-wider bg-surface text-muted px-1.5 py-0.5 rounded border border-border">
                    Synthetic Placeholder
                  </span>
                )}
                {item.legal_reviewed && (
                  <span className="ml-2 text-[9px] uppercase tracking-wider bg-green-500/10 text-green-400 px-1.5 py-0.5 rounded border border-green-500/20">
                    Legal Reviewed
                  </span>
                )}
              </div>
              <p className="text-sm text-muted whitespace-pre-wrap">{item.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
