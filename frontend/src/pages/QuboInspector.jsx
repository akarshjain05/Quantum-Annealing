import { useEffect, useRef, useState } from "react";
import client from "../api/client";
import { Kpi, Loading, EmptyState, ErrorState } from "../components/Common";

function Heatmap({ matrix }) {
  const canvasRef = useRef(null);
  useEffect(() => {
    if (!matrix || !matrix.length) return;
    const n = matrix.length;
    const canvas = canvasRef.current;
    const size = Math.min(560, n * 8);
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext("2d");
    const cell = size / n;

    let min = Infinity, max = -Infinity;
    for (const row of matrix) for (const v of row) { if (v < min) min = v; if (v > max) max = v; }
    const range = max - min || 1;

    for (let i = 0; i < n; i++) {
      for (let j = 0; j < n; j++) {
        const v = matrix[i][j];
        const t = (v - min) / range;
        // negative-cost (favorable) -> teal, positive-cost/penalty -> gold->red
        let r, g, b;
        if (v <= 0) {
          const s = 1 - t * 0.6;
          r = Math.round(16 + 60 * (1 - s)); g = Math.round(120 + 60 * s); b = Math.round(115 + 40 * s);
        } else {
          r = Math.round(120 + 100 * t); g = Math.round(90 - 40 * t); b = Math.round(70 - 30 * t);
        }
        ctx.fillStyle = `rgb(${r},${g},${b})`;
        ctx.fillRect(j * cell, i * cell, Math.ceil(cell), Math.ceil(cell));
      }
    }
  }, [matrix]);

  return <canvas ref={canvasRef} className="rounded-md border border-border" />;
}

export default function QuboInspector() {
  const [runs, setRuns] = useState([]);
  const [runId, setRunId] = useState(null);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    client.get("/api/optimization/runs").then((res) => {
      setRuns(res.data);
      if (res.data.length) setRunId(res.data[0].run_id);
    });
  }, []);

  useEffect(() => {
    if (!runId) return;
    setData(null);
    setError(null);
    client.get(`/api/qubo/${runId}`).then((res) => setData(res.data)).catch(() => setError("Could not load QUBO formulation for this run."));
  }, [runId]);

  if (!runs.length) return <EmptyState title="No optimization runs yet" hint="Run the optimizer first, then inspect its QUBO formulation here." />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl font-semibold">QUBO Inspector</h1>
          <p className="text-sm text-muted mt-1">Technical formulation detail for judge/engineer inspection.</p>
        </div>
        <select value={runId || ""} onChange={(e) => setRunId(Number(e.target.value))} className="bg-raised border border-border rounded-md px-3 py-2 text-sm">
          {runs.map((r) => <option key={r.run_id} value={r.run_id}>Run #{r.run_id} - {new Date(r.created_at).toLocaleString()}</option>)}
        </select>
      </div>

      {error && <ErrorState message={error} />}
      {!data && !error && <Loading label="Rebuilding QUBO formulation" />}

      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Kpi label="Variables" value={data.num_variables} />
            <Kpi label="Dimension" value={`${data.matrix_dimension[0]}x${data.matrix_dimension[1]}`} />
            <Kpi label="Non-zero terms" value={data.num_nonzero_terms} />
            <Kpi label="Sparsity" value={`${data.sparsity_pct}%`} />
            <Kpi label="Final energy" value={data.final_energy?.toFixed(1) ?? "-"} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr] gap-4">
            <div className="card p-4">
              <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-3">
                Q matrix heatmap ({data.num_variables}&times;{data.num_variables})
              </div>
              <Heatmap matrix={data.matrix} />
              <div className="flex items-center gap-4 mt-2 text-[10px] text-muted font-mono">
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: "rgb(76,180,155)" }} /> favorable (negative)</span>
                <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: "rgb(220,50,40)" }} /> costly (positive)</span>
              </div>
            </div>

            <div className="card p-4">
              <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-3">Formulation</div>
              <dl className="text-xs space-y-2 font-mono">
                <Row label="Solver" value={data.solver} />
                <Row label="Buckets ($M)" value={data.buckets_musd.join(", ")} />
                <Row label="One-hot penalty" value={data.penalty_onehot} />
                <Row label="Weights" value={Object.entries(data.weights).map(([k, v]) => `${k}=${v}`).join("  ")} />
                <Row label="Energy offset (constant)" value={data.energy_offset} />
              </dl>
              <div className="text-[11px] uppercase tracking-wide text-muted font-mono mt-4 mb-2">Safety requirements ($M)</div>
              <div className="text-xs font-mono space-y-1 max-h-40 overflow-y-auto scrollbar-thin">
                {Object.entries(data.requirements_musd).map(([cid, req]) => (
                  <div key={cid} className="flex justify-between text-muted"><span>corridor {cid}</span><span className="text-text">{req}</span></div>
                ))}
              </div>
            </div>
          </div>

          <div className="card overflow-hidden">
            <div className="px-4 py-3 border-b border-border text-[11px] uppercase tracking-wide text-muted font-mono">
              Variable map ({data.variable_map.length} binary variables)
            </div>
            <div className="max-h-72 overflow-y-auto scrollbar-thin">
              <table className="w-full text-xs font-mono">
                <thead className="sticky top-0 bg-surface">
                  <tr className="text-muted border-b border-border">
                    <th className="text-left px-4 py-1.5">variable</th>
                    <th className="text-left px-4 py-1.5">corridor</th>
                    <th className="text-right px-4 py-1.5">bucket ($M)</th>
                  </tr>
                </thead>
                <tbody>
                  {data.variable_map.map((v) => (
                    <tr key={v.var_name} className="border-b border-border/40">
                      <td className="px-4 py-1 text-teal">{v.var_name}</td>
                      <td className="px-4 py-1 text-muted">{v.corridor_code}</td>
                      <td className="px-4 py-1 text-right tabular">{v.bucket_value_musd}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="text-[11px] text-faint">{data.note}</div>
        </>
      )}
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-muted">{label}</dt>
      <dd className="text-text text-right">{value}</dd>
    </div>
  );
}
