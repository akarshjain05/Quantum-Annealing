import React, { useEffect, useState } from "react";
import client from "../api/client";
import { Loading, EmptyState } from "../components/Common";

export default function Audit() {
  const [logs, setLogs] = useState(null);
  const [approvals, setApprovals] = useState(null);
  const [verify, setVerify] = useState(null);
  const [pendingApprovals, setPendingApprovals] = useState(null);

  async function handleApprove(runId, decision) {
    try {
      await client.post('/api/optimization/approve', {
        run_id: runId,
        decision: decision,
        reason: decision === "APPROVED" ? "Looks good" : "Requires tuning",
        notes: "Approved from audit dashboard"
      });
      load(); // refresh
    } catch (err) {
      console.error(err);
      alert("Failed to submit decision.");
    }
  }

  const [expandedApproval, setExpandedApproval] = useState(null);
  const [isVerifying, setIsVerifying] = useState(false);

  async function reVerify() {
    setIsVerifying(true);
    // simulate a small delay for dramatic effect in demo
    await new Promise(r => setTimeout(r, 800));
    const v = await client.get("/api/audit/verify");
    setVerify(v.data);
    setIsVerifying(false);
  }


  async function load() {
    const [l, a, v, p] = await Promise.all([
      client.get("/api/audit/log"),
      client.get("/api/audit/approvals"),
      client.get("/api/audit/verify"),
      client.get("/api/optimization/approvals/pending").catch(() => ({ data: [] }))
    ]);
    setLogs(l.data);
    setApprovals(a.data);
    setVerify(v.data);
    setPendingApprovals(p.data);
  }

  useEffect(() => { load(); }, []);

  if (!logs) return <Loading label="Loading audit trail" />;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold">Audit Trail</h1>
        </div>
        {verify && (
          <div className={`tag ${verify.valid ? "tag-practice" : ""}`} style={!verify.valid ? { color: "#D66B56", borderColor: "#D66B56" } : {}}>
            {verify.valid ? `chain valid (${verify.entries_checked} entries)` : `chain broken at #${verify.broken_at_id}`}
          </div>
        )}
      </div>

      {logs.length === 0 ? (
        <EmptyState title="No audit events yet" hint="Run an optimization or record an approval to populate the trail." />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted font-mono">
                <th className="px-4 py-2.5">Event</th>
                <th className="px-4 py-2.5">Actor</th>
                <th className="px-4 py-2.5">Timestamp</th>
                <th className="px-4 py-2.5">Hash</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id} className="border-b border-border/60 align-top">
                  <td className="px-4 py-2.5 font-mono text-teal">{l.event_type}</td>
                  <td className="px-4 py-2.5 text-muted">{l.actor}</td>
                  <td className="px-4 py-2.5 text-muted font-mono">{new Date(l.created_at).toLocaleString()}</td>
                  <td className="px-4 py-2.5 font-mono text-faint">{l.self_hash.slice(0, 16)}...</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      
      <div>
        <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-2 flex items-center justify-between">
          <span>Pending Approvals</span>
        </div>
        {!pendingApprovals ? (
          <div className="text-muted text-xs">Loading...</div>
        ) : pendingApprovals.length === 0 ? (
          <div className="text-muted text-xs mb-6">No optimization runs are currently awaiting approval.</div>
        ) : (
          <div className="card overflow-hidden mb-6 border-gold/30">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted font-mono">
                  <th className="px-4 py-2.5">Run</th>
                  <th className="px-4 py-2.5">Submitted At</th>
                  <th className="px-4 py-2.5">Summary</th>
                  <th className="px-4 py-2.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody>
                {pendingApprovals.map((p) => (
                  <tr key={p.runId} className="border-b border-border/60 hover:bg-surface/50 transition-colors">
                    <td className="px-4 py-2.5 font-mono text-teal">#{p.runNumber}</td>
                    <td className="px-4 py-2.5 text-muted font-mono">{new Date(p.submittedAt).toLocaleString()}</td>
                    <td className="px-4 py-2.5 text-muted">
                      {p.summary.corridorCount} corridors • ${(p.summary.capitalRelease / 1_000_000).toFixed(1)}M released
                    </td>
                    <td className="px-4 py-2.5 text-right space-x-2">
                      <button 
                        onClick={() => handleApprove(p.runNumber, "REJECTED")}
                        className="px-2 py-1 bg-red-900/40 text-red-400 rounded text-[10px] uppercase font-bold hover:bg-red-900/60 transition-colors"
                      >
                        Reject
                      </button>
                      <button 
                        onClick={() => handleApprove(p.runNumber, "APPROVED")}
                        className="px-2 py-1 bg-teal-900/40 text-teal-400 rounded text-[10px] uppercase font-bold hover:bg-teal-900/60 transition-colors"
                      >
                        Approve
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div>
        <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-2">Recorded Decisions</div>
        {approvals && approvals.length === 0 ? (
          <EmptyState title="No approvals recorded" hint="Approve or reject a recommendation from the Optimizer page." />
        ) : (
          <div className="card overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted font-mono">
                  <th className="px-4 py-2.5">Run</th>
                  <th className="px-4 py-2.5">Decision</th>
                  <th className="px-4 py-2.5">Timestamp</th>
                  <th className="px-4 py-2.5"></th>
                </tr>
              </thead>
              <tbody>
                {approvals?.map((a) => (
                  <React.Fragment key={a.id}>
                    <tr 
                      className="border-b border-border/60 hover:bg-surface/50 cursor-pointer transition-colors"
                      onClick={() => setExpandedApproval(expandedApproval === a.run_id ? null : a.run_id)}
                    >
                      <td className="px-4 py-2.5 font-mono text-teal">#{a.run_id}</td>
                      <td className="px-4 py-2.5 font-medium">{a.decision}</td>
                      <td className="px-4 py-2.5 text-muted font-mono">{new Date(a.created_at).toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right text-teal">{expandedApproval === a.run_id ? "Hide details" : "View rationale"}</td>
                    </tr>
                    {expandedApproval === a.run_id && (
                      <tr>
                        <td colSpan="4" className="p-4 bg-bg/50">
                          <DecisionRationale runId={a.run_id} />
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function DecisionRationale({ runId }) {
  const [details, setDetails] = useState(null);
  
  useEffect(() => {
    client.get(`/api/audit/decision-rationale/${runId}`)
      .then(r => setDetails(r.data))
      .catch(err => console.error(err));
  }, [runId]);
  
  if (!details) return <div className="text-muted text-sm p-4">Loading rationale...</div>;
  
  return (
    <div className="mt-4 bg-surface/50 p-6 rounded-md border border-border">
      <h3 className="font-medium text-teal mb-3 flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-teal"></span>
        Decision Rationale - Run #{details.runNumber}
      </h3>
      
      <p className="text-sm text-muted mb-6">
        This record documents why ${(details.capitalReleased / 1_000_000).toFixed(1)}M 
        capital release was recommended and <span className="font-mono text-text">{details.status}</span> on {new Date(details.decidedAt).toLocaleString()}.
      </p>
      
      <div className="grid md:grid-cols-2 gap-6">
        <div className="space-y-3">
          <div className="text-[11px] uppercase tracking-wide text-muted font-mono border-b border-border/50 pb-1">
            Calculation Methodology
          </div>
          <p className="text-xs text-muted">
            For each corridor, the minimum safe balance was calculated as:
          </p>
          <div className="bg-bg p-3 rounded font-mono text-xs border border-border/50 text-faint">
            Minimum = P{details.confidenceLevel}(Historical Demand)<br/>
            + Safety Buffer ({(details.safetyBuffer * 100).toFixed(0)}%)<br/>
            + FX Volatility Reserve<br/>
            + Correspondent Risk Margin
          </div>
        </div>
        
        <div className="space-y-3">
          <div className="text-[11px] uppercase tracking-wide text-muted font-mono border-b border-border/50 pb-1">
            Example - {details.exampleCorridor.code}
          </div>
          <div className="bg-bg p-3 rounded text-xs border border-border/50 space-y-1.5 font-mono">
            <div className="flex justify-between">
              <span className="text-muted">P{details.confidenceLevel} Historical Demand</span>
              <span>${(details.exampleCorridor.p95Demand / 1_000_000).toFixed(1)}M</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">Safety Buffer ({(details.safetyBuffer * 100).toFixed(0)}%)</span>
              <span>${(details.exampleCorridor.safetyBuffer / 1_000_000).toFixed(1)}M</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted">FX Reserve</span>
              <span>${(details.exampleCorridor.fxReserve / 1_000_000).toFixed(1)}M</span>
            </div>
            <div className="flex justify-between border-b border-border/50 pb-1.5">
              <span className="text-muted">Correspondent Margin</span>
              <span>${(details.exampleCorridor.correspondentMargin / 1_000_000).toFixed(1)}M</span>
            </div>
            <div className="flex justify-between pt-0.5 font-medium">
              <span className="text-teal">Minimum Required</span>
              <span className="text-teal">${(details.exampleCorridor.minimumRequired / 1_000_000).toFixed(1)}M</span>
            </div>
            <div className="flex justify-between pt-2">
              <span className="text-muted">Current Balance</span>
              <span>${(details.exampleCorridor.currentBalance / 1_000_000).toFixed(1)}M</span>
            </div>
            <div className="flex justify-between pt-0.5 font-medium">
              <span className="text-gold">Excess Capital</span>
              <span className="text-gold">${(details.exampleCorridor.excess / 1_000_000).toFixed(1)}M</span>
            </div>
          </div>
        </div>
      </div>
      
      {details.approverNotes && (
        <div className="mt-6 pt-4 border-t border-border/50">
          <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-2">
            Approver Notes
          </div>
          <blockquote className="border-l-2 border-teal pl-3 text-sm italic text-muted">
            "{details.approverNotes}"
            <footer className="mt-1 text-xs not-italic font-mono text-faint">— {details.approvedBy}</footer>
          </blockquote>
        </div>
      )}
      
      <div className="mt-6 p-4 rounded bg-bg border border-border/50">
        <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-3">
          Cryptographic Proof
        </div>
        <div className="grid grid-cols-[100px_1fr] gap-y-2 text-xs font-mono">
          <div className="text-muted">Record Hash:</div>
          <div className="text-teal truncate" title={details.hash}>{details.hash}</div>
          <div className="text-muted">Prev Hash:</div>
          <div className="text-faint truncate" title={details.previousHash}>{details.previousHash}</div>
          <div className="text-muted">Timestamp:</div>
          <div className="text-faint">{details.timestamp}</div>
        </div>
      </div>
    </div>
  );
}
