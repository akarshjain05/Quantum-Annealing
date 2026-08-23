import { useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import client from "../api/client";
import { Loading } from "../components/Common";

export default function StressTests() {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [lossResult, setLossResult] = useState(null);
  const [runningLoss, setRunningLoss] = useState(false);

  async function runLossSensitivity() {
    setRunningLoss(true);
    setLossResult(null);
    try {
      const res = await api.get('/optimization/loss-sensitivity');
      setLossResult(res.data);
    } finally {
      setRunningLoss(false);
    }
  }

  async function run() {
    setRunning(true);
    setResult(null);
    try {
      const res = await client.post("/api/stress-tests/run", {});
      setResult(res.data);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Stress Tests</h1>
        <p className="text-sm text-muted mt-1">Run 8 predefined shock scenarios against every corridor and compare against the current baseline.</p>
      </div>

      <button onClick={run} disabled={running} className="bg-red text-bg font-medium text-sm rounded-md px-4 py-2.5 hover:bg-red/90 disabled:opacity-60">
        {running ? "Running stress battery..." : "Run stress test battery"}
      </button>

      {running && <Loading label="Running 8 scenarios" />}

      {result && (
        <div className="space-y-4">
          <div className="card p-4">
            <div className="text-[11px] uppercase tracking-wide text-muted font-mono">Baseline liquidity</div>
            <div className="font-display text-2xl tabular mt-1">${result.baseline_liquidity_musd.toFixed(1)}M</div>
          </div>

          <div className="card p-4">
            <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-3">Recommended liquidity by scenario ($M)</div>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={result.scenarios} margin={{ bottom: 70 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#263041" />
                <XAxis dataKey="scenario_name" stroke="#7C8AA0" fontSize={9} angle={-35} textAnchor="end" interval={0} height={90} />
                <YAxis stroke="#7C8AA0" fontSize={11} />
                <Tooltip contentStyle={{ background: "#171E27", border: "1px solid #263041", fontSize: 12 }} />
                <Bar dataKey="recommended_liquidity_musd" radius={[3, 3, 0, 0]}>
                  {result.scenarios.map((s, i) => (
                    <Cell key={i} fill={s.delta_vs_baseline_musd > 0 ? "#D66B56" : "#4FB8AE"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card overflow-hidden">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted font-mono">
                  <th className="px-4 py-2.5">Scenario</th>
                  <th className="px-4 py-2.5 text-right">Required ($M)</th>
                  <th className="px-4 py-2.5 text-right">Recommended ($M)</th>
                  <th className="px-4 py-2.5 text-right">vs. baseline</th>
                  <th className="px-4 py-2.5 text-right">Coverage</th>
                  <th className="px-4 py-2.5 text-right">Shortfall p</th>
                </tr>
              </thead>

              <tbody>
                {result.scenarios.map((s) => {
                  const maxRequired = Math.max(...result.scenarios.map(sc => sc.required_liquidity_musd));
                  const isWorst = s.required_liquidity_musd === maxRequired;
                  return (
                  <tr key={s.scenario_name} className={`border-b border-border/60 ${isWorst ? "bg-red/10" : ""}`}>
                    <td className="px-4 py-2.5 flex items-center gap-2">
                      {s.scenario_name}
                      {isWorst && <span className="bg-red text-bg text-[10px] uppercase font-bold px-1.5 py-0.5 rounded">Worst Case</span>}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular">{s.required_liquidity_musd.toFixed(1)}</td>

                    <td className="px-4 py-2.5 text-right font-mono tabular">{s.recommended_liquidity_musd.toFixed(1)}</td>
                    <td className={`px-4 py-2.5 text-right font-mono tabular ${s.delta_vs_baseline_musd > 0 ? "text-red" : "text-teal"}`}>
                      {s.delta_vs_baseline_musd >= 0 ? "+" : ""}{s.delta_vs_baseline_musd.toFixed(1)}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular">{(s.settlement_coverage * 100).toFixed(1)}%</td>
                    <td className="px-4 py-2.5 text-right font-mono tabular">{(s.shortfall_probability * 100).toFixed(2)}%</td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="mt-12 pt-8 border-t border-border/60">
        <h2 className="font-display text-xl font-semibold">Phase B: Loss-Given-Shortfall Sensitivity Analysis</h2>
        <p className="text-sm text-muted mt-1 mb-4">Because the reputational/operational cost of a settlement failure cannot be empirically validated, we sweep a multiplier across the assumed baseline ($5M). This proves the robustness of the quantum optimizer's recommendations under varying loss regimes.</p>

        <button onClick={runLossSensitivity} disabled={runningLoss} className="bg-primary text-bg font-medium text-sm rounded-md px-4 py-2.5 hover:bg-primary/90 disabled:opacity-60 mb-6">
          {runningLoss ? "Running Sensitivity Sweep..." : "Run Multiplier Sweep"}
        </button>

        {runningLoss && <Loading label="Evaluating multipliers [0.5x, 1.0x, 1.5x, 2.0x, 3.0x]" />}

        {lossResult && (
          <div className="card overflow-hidden">
            <table className="w-full text-sm text-left">
              <thead className="text-[11px] uppercase tracking-wide text-muted font-mono border-b border-border bg-subtle">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Assumed Loss Multiplier</th>
                  <th className="px-4 py-2.5 font-medium text-right">Rec. Liquidity ($M)</th>
                  <th className="px-4 py-2.5 font-medium text-right">Capital Released ($M)</th>
                  <th className="px-4 py-2.5 font-medium text-right">Stability</th>
                </tr>
              </thead>
              <tbody>
                {lossResult.sweep.map((s) => {
                  const isBaseline = s.multiplier === 1.0;
                  // If multiplier > 1 and capital released decreases, that means it got more conservative
                  const baselineRun = lossResult.sweep.find(x => x.multiplier === 1.0);
                  const stability = s.capital_released_musd === baselineRun.capital_released_musd ? 
                    <span className="text-teal font-medium">Stable</span> : 
                    <span className="text-amber font-medium">Sensitive (shifted)</span>;
                  
                  return (
                    <tr key={s.multiplier} className={`border-b border-border/60 ${isBaseline ? 'bg-primary/5' : ''}`}>
                      <td className="px-4 py-2.5 flex items-center gap-2">
                        {s.multiplier.toFixed(1)}x
                        {isBaseline && <span className="bg-primary/20 text-primary text-[10px] uppercase font-bold px-1.5 py-0.5 rounded">Current Baseline</span>}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular">{s.total_recommended_musd.toFixed(1)}</td>
                      <td className="px-4 py-2.5 text-right font-mono tabular">{s.capital_released_musd.toFixed(1)}</td>
                      <td className="px-4 py-2.5 text-right tabular">{stability}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
