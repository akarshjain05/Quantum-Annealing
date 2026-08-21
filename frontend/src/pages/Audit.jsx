import { useEffect, useState } from "react";
import client from "../api/client";
import { Loading, EmptyState } from "../components/Common";

export default function Audit() {
  const [logs, setLogs] = useState(null);
  const [approvals, setApprovals] = useState(null);
  const [verify, setVerify] = useState(null);

  async function load() {
    const [l, a, v] = await Promise.all([
      client.get("/api/audit/log"),
      client.get("/api/audit/approvals"),
      client.get("/api/audit/verify"),
    ]);
    setLogs(l.data);
    setApprovals(a.data);
    setVerify(v.data);
  }

  useEffect(() => { load(); }, []);

  if (!logs) return <Loading label="Loading audit trail" />;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold">Audit Trail</h1>
          <p className="text-sm text-muted mt-1">Tamper-evident hash chain - not a blockchain, an append-only signed log.</p>
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
        <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-2">Human approvals</div>
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
                </tr>
              </thead>
              <tbody>
                {approvals?.map((a) => (
                  <tr key={a.id} className="border-b border-border/60">
                    <td className="px-4 py-2.5 font-mono">#{a.run_id}</td>
                    <td className="px-4 py-2.5">{a.decision}</td>
                    <td className="px-4 py-2.5 text-muted font-mono">{new Date(a.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
