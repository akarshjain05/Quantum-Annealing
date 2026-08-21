import { useState, useEffect } from 'react';
import client from '../api/client';

function formatRelativeTime(dateString) {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now - date) / 1000);
  
  if (diffInSeconds < 60) return 'just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`;
  return `${Math.floor(diffInSeconds / 86400)} days ago`;
}

export default function Approvals() {
  const [pendingApprovals, setPendingApprovals] = useState([]);
  
  useEffect(() => {
    client.get('/api/optimization/approvals/pending')
      .then(r => setPendingApprovals(r.data))
      .catch(err => console.error("Error fetching approvals:", err));
  }, []);

  const handleDecision = async (runId, decision, notes, rejectionReason) => {
    try {
      await client.post(`/api/optimization/runs/${runId}/decide`, { 
        decision, 
        notes, 
        rejection_reason: rejectionReason,
        decided_by: 'treasury@demo-bank.com' 
      });
      // Refresh pending list
      setPendingApprovals(prev => prev.filter(a => a.runId !== runId));
    } catch (err) {
      console.error("Error submitting decision:", err);
      alert("Failed to submit decision");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Approvals Center</h1>
        <p className="text-sm text-muted mt-1">
          Review and approve liquidity optimization recommendations
        </p>
      </div>

      <div className="space-y-4">
        <h2 className="text-[11px] uppercase tracking-wide text-muted font-mono border-b border-border pb-2">
          Pending My Approval ({pendingApprovals.length})
        </h2>
        
        {pendingApprovals.length === 0 ? (
          <div className="card p-8 text-center text-muted text-sm border-dashed">
            No pending approvals
          </div>
        ) : (
          <div className="space-y-4">
            {pendingApprovals.map(approval => (
              <ApprovalCard 
                key={approval.runId} 
                approval={approval} 
                onDecision={handleDecision} 
              />
            ))}
          </div>
        )}
      </div>

      <div className="pt-8 space-y-4">
        <h2 className="text-[11px] uppercase tracking-wide text-muted font-mono border-b border-border pb-2">
          Recent Approval History
        </h2>
        <div className="card p-8 text-center text-muted text-sm border-dashed">
          History log will appear here
        </div>
      </div>
    </div>
  );
}

function ApprovalCard({ approval, onDecision }) {
  const [decision, setDecision] = useState(null);
  const [notes, setNotes] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');
  
  return (
    <div className="card p-5 space-y-5">
      <div className="flex items-center justify-between border-b border-border/50 pb-4">
        <div>
          <h3 className="font-medium text-lg">Optimization Run #{approval.runNumber}</h3>
          <div className="text-xs text-muted mt-1 font-mono">
            Submitted {formatRelativeTime(approval.submittedAt)} by {approval.submittedBy}
          </div>
        </div>
        <div className="px-3 py-1 bg-gold/10 text-gold text-xs rounded-full border border-gold/20 font-medium">
          Pending Review
        </div>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-surface/30 p-4 rounded-md border border-border/40">
        <div>
          <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-1">Corridors</div>
          <div className="text-xl font-medium">{approval.summary.corridorCount}</div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-1">Capital Release</div>
          <div className="text-xl font-medium text-teal">
            ${(approval.summary.capitalRelease / 1_000_000).toFixed(1)}M
          </div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-1">Annual Savings</div>
          <div className="text-xl font-medium text-gold">
            ${(approval.summary.annualSavings / 1_000_000).toFixed(1)}M
          </div>
        </div>
        <div>
          <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-1">Safety Check</div>
          <div className={`text-sm font-medium mt-1 ${approval.summary.allSafetyMet ? 'text-teal' : 'text-red'}`}>
            {approval.summary.allSafetyMet ? '✓ Passed constraints' : '⚠ Review violations'}
          </div>
        </div>
      </div>
      
      {approval.notes && (
        <div className="text-sm bg-surface p-3 rounded border border-border italic text-muted">
          Submitter notes: "{approval.notes}"
        </div>
      )}
      
      <div className="space-y-4 pt-2">
        <div className="text-[11px] uppercase tracking-wide text-muted font-mono">Your Decision:</div>
        
        <div className="flex gap-4">
          <label className={`flex items-center gap-2 cursor-pointer p-2 rounded border ${decision === 'APPROVED' ? 'border-teal bg-teal/10 text-teal' : 'border-border bg-surface hover:border-teal/50'}`}>
            <input type="radio" name={`dec-${approval.runId}`} className="accent-teal" checked={decision === 'APPROVED'} onChange={() => setDecision('APPROVED')} />
            <span className="text-sm font-medium">Approve</span>
          </label>
          <label className={`flex items-center gap-2 cursor-pointer p-2 rounded border ${decision === 'REJECTED' ? 'border-red bg-red/10 text-red' : 'border-border bg-surface hover:border-red/50'}`}>
            <input type="radio" name={`dec-${approval.runId}`} className="accent-red" checked={decision === 'REJECTED'} onChange={() => setDecision('REJECTED')} />
            <span className="text-sm font-medium">Reject</span>
          </label>
          <label className={`flex items-center gap-2 cursor-pointer p-2 rounded border ${decision === 'MORE_INFO' ? 'border-gold bg-gold/10 text-gold' : 'border-border bg-surface hover:border-gold/50'}`}>
            <input type="radio" name={`dec-${approval.runId}`} className="accent-gold" checked={decision === 'MORE_INFO'} onChange={() => setDecision('MORE_INFO')} />
            <span className="text-sm font-medium">Request More Info</span>
          </label>
        </div>
        
        {decision === 'REJECTED' && (
          <div>
            <label className="text-[11px] uppercase tracking-wide text-red/80 font-mono mb-1 block">Rejection reason (required):</label>
            <textarea 
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              className="w-full bg-surface border border-red/40 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-red/70 text-text"
              rows={2}
              placeholder="Explain why this recommendation should not be implemented..."
            />
          </div>
        )}
        
        <div>
          <label className="text-[11px] uppercase tracking-wide text-muted font-mono mb-1 block">Notes (optional):</label>
          <textarea 
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full bg-surface border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:border-teal/50 text-text"
            rows={2}
          />
        </div>
        
        <div className="flex justify-end gap-3 pt-2">
          <button 
            className="px-4 py-2 bg-surface hover:bg-raised border border-border rounded-md text-sm transition-colors"
            onClick={() => alert(`In a real app, this would route to /optimizer/run/${approval.runId}`)}
          >
            View Full Details
          </button>
          <button 
            className="px-6 py-2 bg-teal text-bg font-medium hover:bg-teal/90 rounded-md text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            disabled={!decision || (decision === 'REJECTED' && !rejectionReason.trim())}
            onClick={() => onDecision(approval.runId, decision, notes, rejectionReason)}
          >
            Submit Decision
          </button>
        </div>
      </div>
    </div>
  );
}
