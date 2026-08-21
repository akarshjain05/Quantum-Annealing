import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import client from "../api/client";
import { Loading } from "../components/Common";

export default function Scenarios() {
  const [corridors, setCorridors] = useState([]);
  const [selected, setSelected] = useState("");
  const [confidence, setConfidence] = useState(0.95);
  const [demandDelta, setDemandDelta] = useState(30);
  const [volDelta, setVolDelta] = useState(0);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    client.get("/api/corridors").then((res) => setCorridors(res.data));
  }, []);

  async function run() {
    setRunning(true);
    setResult(null);
    const label = `${selected || "All corridors"}: demand ${demandDelta >= 0 ? "+" : ""}${demandDelta}%, volatility ${volDelta >= 0 ? "+" : ""}${volDelta}%, ${(confidence * 100).toFixed(1)}% confidence`;
    try {
      const res = await client.post("/api/scenarios/run", {
        corridors: selected ? [selected] : null,
        confidence_level: confidence,
        demand_delta_pct: demandDelta,
        volatility_delta_pct: volDelta,
        label,
      });
      setResult(res.data);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Scenario Simulator</h1>
        <p className="text-sm text-muted mt-1">Adjust assumptions and re-run the optimizer to see how the recommendation shifts.</p>
      </div>

      <div className="card p-4 grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
        <Field label="Corridor">
          <select value={selected} onChange={(e) => setSelected(e.target.value)} className="input">
            <option value="">All corridors</option>
            {corridors.map((c) => <option key={c.code} value={c.code}>{c.code}</option>)}
          </select>
        </Field>
        <Field label="Confidence level">
          <select value={confidence} onChange={(e) => setConfidence(Number(e.target.value))} className="input">
            <option value={0.90}>90%</option>
            <option value={0.95}>95%</option>
            <option value={0.99}>99%</option>
            <option value={0.999}>99.9%</option>
          </select>
        </Field>
        <Field label={`Demand change: ${demandDelta >= 0 ? "+" : ""}${demandDelta}%`}>
          <input type="range" min="-50" max="100" value={demandDelta} onChange={(e) => setDemandDelta(Number(e.target.value))} className="w-full accent-teal" />
        </Field>
        <Field label={`Volatility change: ${volDelta >= 0 ? "+" : ""}${volDelta}%`}>
          <input type="range" min="-50" max="100" value={volDelta} onChange={(e) => setVolDelta(Number(e.target.value))} className="w-full accent-teal" />
        </Field>
      </div>

      <button onClick={run} disabled={running} className="bg-teal text-bg font-medium text-sm rounded-md px-4 py-2.5 hover:bg-teal/90 disabled:opacity-60">
        {running ? "Running scenario..." : "Run scenario"}
      </button>

      {running && <Loading label="Re-running optimizer under new assumptions" />}

      {result && (
        <div className="space-y-4">
          <div className="card p-4">
            <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-1">{result.label}</div>
            <div className="flex items-baseline gap-6 mt-2">
              <div>
                <div className="text-xs text-muted">Before</div>
                <div className="font-display text-2xl tabular">${result.aggregate_before_musd.toFixed(1)}M</div>
              </div>
              <div className="text-2xl text-faint">&rarr;</div>
              <div>
                <div className="text-xs text-muted">After</div>
                <div className="font-display text-2xl tabular text-teal">${result.aggregate_after_musd.toFixed(1)}M</div>
              </div>
              <div className="ml-auto text-right">
                <div className="text-xs text-muted">Change</div>
                <div className={`font-display text-2xl tabular ${result.aggregate_after_musd >= result.aggregate_before_musd ? "text-red" : "text-gold"}`}>
                  {result.aggregate_after_musd >= result.aggregate_before_musd ? "+" : ""}
                  ${(result.aggregate_after_musd - result.aggregate_before_musd).toFixed(1)}M
                </div>
              </div>
            </div>
          </div>

          <div className="card p-4">
            <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-3">Per-corridor comparison ($M)</div>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={result.comparison}>
                <CartesianGrid strokeDasharray="3 3" stroke="#263041" />
                <XAxis dataKey="corridor_code" stroke="#7C8AA0" fontSize={10} angle={-35} textAnchor="end" height={60} />
                <YAxis stroke="#7C8AA0" fontSize={11} />
                <Tooltip contentStyle={{ background: "#171E27", border: "1px solid #263041", fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="before_optimized_musd" name="Before" fill="#7C8AA0" radius={[3, 3, 0, 0]} />
                <Bar dataKey="after_optimized_musd" name="After" fill="#C7A24C" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <style>{`.input { background:#171E27; border:1px solid #263041; border-radius:6px; padding:0.5rem 0.65rem; font-size:0.8rem; color:#E7ECF3; width:100%; }`}</style>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block text-[11px] text-muted mb-1 font-mono uppercase tracking-wide truncate">{label}</span>
      {children}
    </label>
  );
}
