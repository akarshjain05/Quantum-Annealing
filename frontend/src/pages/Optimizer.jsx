import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Legend } from "recharts";
import client from "../api/client";
import { Kpi } from "../components/Common";

const STAGES = [
  "Building QUBO...",
  "Generating one-hot and shortfall constraints...",
  "Running simulated annealing...",
  "Refining one-hot blocks...",
  "Validating constraints...",
  "Generating recommendation...",
];

export default function Optimizer() {
  const [confidence, setConfidence] = useState(0.95);
  const [iterations, setIterations] = useState(8000);
  const [initialTemp, setInitialTemp] = useState(1000);
  const [coolingRate, setCoolingRate] = useState(0.995);
  const [running, setRunning] = useState(false);
  const [stage, setStage] = useState(-1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [approvalStatus, setApprovalStatus] = useState(null);
  const [expandedCorridor, setExpandedCorridor] = useState(null);

  async function runOptimization() {
    setRunning(true);
    setError(null);
    setResult(null);
    setApprovalStatus(null);
    setStage(0);

    const stageTimer = setInterval(() => {
      setStage((s) => Math.min(s + 1, STAGES.length - 2));
    }, 220);

    try {
      const res = await client.post("/api/optimization/run", {
        confidence_level: confidence,
        iterations,
        initial_temperature: initialTemp,
        cooling_rate: coolingRate,
      });
      clearInterval(stageTimer);
      setStage(STAGES.length - 1);
      setTimeout(() => {
        setResult(res.data);
        setRunning(false);
      }, 300);
    } catch (err) {
      clearInterval(stageTimer);
      setRunning(false);
      setError(err.response?.data?.detail || "Optimization could not produce a valid solution.");
    }
  }

  async function approve(decision) {
    if (!result) return;
    await client.post("/api/optimization/approve", { run_id: result.run_id, decision });
    setApprovalStatus(decision);
  }

  const convergenceData = result?.convergence_history?.map((e, i) => ({ step: i, energy: e })) || [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Optimizer</h1>
        <p className="text-sm text-muted mt-1">
          QUBO-based liquidity allocation, solved today via simulated annealing. Quantum-ready formulation, not live quantum execution.
        </p>
      </div>

      <div className="card p-4">
        <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-3">Inputs</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Field label="Confidence level">
            <select value={confidence} onChange={(e) => setConfidence(Number(e.target.value))} className="input">
              <option value={0.90}>90%</option>
              <option value={0.95}>95%</option>
              <option value={0.99}>99%</option>
              <option value={0.999}>99.9%</option>
            </select>
          </Field>
          <Field label="Iterations"><input type="number" value={iterations} onChange={(e) => setIterations(Number(e.target.value))} className="input" /></Field>
          <Field label="Initial temperature"><input type="number" value={initialTemp} onChange={(e) => setInitialTemp(Number(e.target.value))} className="input" /></Field>
          <Field label="Cooling rate"><input type="number" step="0.001" value={coolingRate} onChange={(e) => setCoolingRate(Number(e.target.value))} className="input" /></Field>
        </div>
        <button
          onClick={runOptimization}
          disabled={running}
          className="mt-4 bg-teal text-bg font-medium text-sm rounded-md px-4 py-2.5 hover:bg-teal/90 transition-colors disabled:opacity-60"
        >
          {running ? "Optimizing..." : "Run optimization"}
        </button>
      </div>

      {running && (
        <div className="card p-4">
          <div className="space-y-1.5">
            {STAGES.map((s, i) => (
              <div key={s} className={`flex items-center gap-2 text-sm transition-colors ${i <= stage ? "text-text" : "text-faint"}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${i < stage ? "bg-teal" : i === stage ? "bg-gold animate-pulse" : "bg-faint"}`} />
                {s}
              </div>
            ))}
          </div>
        </div>
      )}

      {error && <div className="card border-red/40 p-4 text-red text-sm">{error}</div>}

      {result && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Kpi label="Current liquidity" value={`$${result.current_liquidity_musd.toFixed(1)}M`} />
            <Kpi label="Optimized liquidity" value={`$${result.optimized_liquidity_musd.toFixed(1)}M`} tone="teal" />
            <Kpi
              label="Capital released"
              value={`${result.capital_released_musd >= 0 ? "" : "-"}$${Math.abs(result.capital_released_musd).toFixed(1)}M`}
              tone={result.capital_released_musd >= 0 ? "gold" : "red"}
            />
            <Kpi label="QUBO energy (final)" value={result.final_energy.toFixed(1)} sub={`from ${result.initial_energy.toFixed(0)}`} />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Kpi label="Variables" value={result.qubo_variables} />
            <Kpi label="Non-zero terms" value={result.qubo_terms} />
            <Kpi label="Runtime" value={`${result.runtime_ms.toFixed(0)}ms`} />
            <Kpi
              label="Constraint satisfaction"
              value={result.constraint_violations.length === 0 ? "Clean" : `${result.constraint_violations.length} flagged`}
              tone={result.constraint_violations.length === 0 ? "teal" : "gold"}
            />
          </div>

          {result.constraint_violations.length > 0 && (
            <div className="card border-gold/30 p-3 space-y-1">
              {result.constraint_violations.map((v, i) => (
                <div key={i} className="text-xs text-gold font-mono">
                  {v.corridor_code}: {v.type} - required ${v.required_musd}M, selected ${v.selected_musd}M
                  {v.note ? ` (${v.note})` : ""}
                </div>
              ))}
            </div>
          )}

          <div className="card p-4">
            <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-3">Convergence</div>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={convergenceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#263041" />
                <XAxis dataKey="step" stroke="#7C8AA0" fontSize={11} label={{ value: "iteration (sampled)", position: "insideBottom", offset: -3, fontSize: 10, fill: "#7C8AA0" }} />
                <YAxis stroke="#7C8AA0" fontSize={11} />
                <Tooltip contentStyle={{ background: "#171E27", border: "1px solid #263041", fontSize: 12 }} />
                <Line type="monotone" dataKey="energy" stroke="#4FB8AE" dot={false} strokeWidth={1.5} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="card p-4">
            <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-3">Before vs. after, by corridor ($M)</div>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={result.corridor_results.map((r) => ({ ...r, code: r.explanation.corridor_code }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#263041" />
                <XAxis dataKey="code" stroke="#7C8AA0" fontSize={10} angle={-35} textAnchor="end" height={60} />
                <YAxis stroke="#7C8AA0" fontSize={11} />
                <Tooltip contentStyle={{ background: "#171E27", border: "1px solid #263041", fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="current_liquidity_musd" name="Current" fill="#7C8AA0" radius={[3, 3, 0, 0]} />
                <Bar dataKey="optimized_liquidity_musd" name="Optimized" fill="#4FB8AE" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card overflow-hidden">
            <div className="px-4 py-3 border-b border-border text-[11px] uppercase tracking-wide text-muted font-mono">
              Per-corridor recommendations
            </div>
            {result.corridor_results.map((r) => {
              const code = r.explanation.corridor_code;
              const isOpen = expandedCorridor === code;
              return (
                <div key={code} className="border-b border-border/60 last:border-0">
                  <button
                    onClick={() => setExpandedCorridor(isOpen ? null : code)}
                    className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-raised/40 transition-colors"
                  >
                    <span className="font-mono text-sm">{code}</span>
                    <span className="text-sm text-muted flex-1 mx-4 truncate">{r.explanation.headline}</span>
                    <span className="text-xs text-teal">{isOpen ? "hide" : "why?"}</span>
                  </button>
                  {isOpen && (
                    <div className="px-4 pb-4 text-sm space-y-3">
                      <ul className="list-disc list-inside text-muted space-y-1 text-xs">
                        {r.explanation.reasons.map((reason, i) => <li key={i}>{reason}</li>)}
                      </ul>
                      <div>
                        <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-1">Model assumptions</div>
                        <ul className="list-disc list-inside text-faint space-y-0.5 text-xs">
                          {r.explanation.model_assumptions.map((a, i) => <li key={i}>{a}</li>)}
                        </ul>
                      </div>
                      <div className="flex gap-4 text-xs font-mono pt-1">
                        <span className="text-muted">baselines:</span>
                        {Object.entries(r.baselines).map(([k, v]) => (
                          <span key={k} className={k === "quantum_inspired" ? "text-teal" : "text-muted"}>{k}: ${v}M</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <div className="card p-4 flex items-center justify-between">
            <div className="text-sm text-muted">
              {approvalStatus ? (
                <span className="text-teal">Recorded: {approvalStatus.replace("_", " ").toLowerCase()}. Decision-support prototype - no live financial transaction is executed.</span>
              ) : (
                "This recommendation requires human review before any hypothetical execution."
              )}
            </div>
            {!approvalStatus && (
              <div className="flex gap-2">
                <button onClick={() => approve("APPROVED")} className="text-xs px-3 py-1.5 rounded-md bg-teal text-bg font-medium hover:bg-teal/90">Approve</button>
                <button onClick={() => approve("RECALCULATION_REQUESTED")} className="text-xs px-3 py-1.5 rounded-md border border-border text-muted hover:text-text">Request recalculation</button>
                <button onClick={() => approve("REJECTED")} className="text-xs px-3 py-1.5 rounded-md border border-red/40 text-red hover:bg-red/10">Reject</button>
              </div>
            )}
          </div>
        </>
      )}

      <style>{`.input { background:#171E27; border:1px solid #263041; border-radius:6px; padding:0.5rem 0.65rem; font-size:0.8rem; color:#E7ECF3; width:100%; }`}</style>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block text-[11px] text-muted mb-1 font-mono uppercase tracking-wide">{label}</span>
      {children}
    </label>
  );
}
