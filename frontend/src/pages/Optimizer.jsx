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

const RISK_APPETITE_MAP = {
  very_conservative: { confidence: 0.99, safetyBuffer: 0.10, expectedRelease: '5-10%', label: 'Very Conservative' },
  conservative:      { confidence: 0.95, safetyBuffer: 0.05, expectedRelease: '15-25%', label: 'Conservative' },
  balanced:          { confidence: 0.90, safetyBuffer: 0.03, expectedRelease: '20-30%', label: 'Balanced' },
  efficient:         { confidence: 0.85, safetyBuffer: 0.02, expectedRelease: '25-35%', label: 'Efficient' },
  very_efficient:    { confidence: 0.80, safetyBuffer: 0.01, expectedRelease: '30-40%', label: 'Very Efficient' },
};

const defaultConfig = {
  riskAppetite: 'balanced',
  corridorsIncluded: [],
  globalCap: "",
  iterations: 8000,
  initialTemperature: 1000,
  coolingRate: 0.995,
};

export default function Optimizer() {
  const [step, setStep] = useState(1);
  const [config, setConfig] = useState(defaultConfig);
  const [results, setResults] = useState(null);
  const [availableCorridors, setAvailableCorridors] = useState([]);

  useEffect(() => {
    client.get("/api/corridors").then(res => {
      setAvailableCorridors(res.data);
      setConfig(prev => ({ ...prev, corridorsIncluded: res.data.map(c => c.code) }));
    }).catch(err => console.error(err));
  }, []);

  return (
    <div className="space-y-6 pb-12">
      {/* Step Indicator */}
      <div className="mb-6">
        <h1 className="font-display text-2xl font-semibold">Liquidity Optimizer</h1>
        <p className="text-sm text-muted mt-1">
          Configure, run, and review liquidity optimization recommendations
        </p>
        
        <div className="flex items-center gap-2 mt-6">
          <div className={`flex items-center gap-2 ${step >= 1 ? 'text-teal' : 'text-muted'}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${step >= 1 ? 'bg-teal/20 text-teal' : 'bg-surface'}`}>1</div>
            <span className="text-sm font-medium">Configure</span>
          </div>
          <div className={`w-8 h-[1px] ${step >= 2 ? 'bg-teal/50' : 'bg-border'}`}></div>
          <div className={`flex items-center gap-2 ${step >= 2 ? 'text-teal' : 'text-muted'}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${step >= 2 ? 'bg-teal/20 text-teal' : 'bg-surface'}`}>2</div>
            <span className="text-sm font-medium">Run</span>
          </div>
          <div className={`w-8 h-[1px] ${step >= 3 ? 'bg-teal/50' : 'bg-border'}`}></div>
          <div className={`flex items-center gap-2 ${step >= 3 ? 'text-teal' : 'text-muted'}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${step >= 3 ? 'bg-teal/20 text-teal' : 'bg-surface'}`}>3</div>
            <span className="text-sm font-medium">Review</span>
          </div>
        </div>
      </div>

      {/* Step Content */}
      {step === 1 && (
        <ConfigureStep 
          config={config} 
          onChange={setConfig} 
          onNext={() => setStep(2)} 
          availableCorridors={availableCorridors}
        />
      )}
      {step === 2 && (
        <RunStep 
          config={config} 
          onComplete={(r) => { setResults(r); setStep(3); }} 
          onCancel={() => setStep(1)} 
        />
      )}
      {step === 3 && (
        <ReviewStep 
          results={results} 
          onStartOver={() => { setStep(1); setResults(null); }} 
        />
      )}
      <style>{`.input { background:#171E27; border:1px solid #263041; border-radius:6px; padding:0.5rem 0.65rem; font-size:0.8rem; color:#E7ECF3; width:100%; }`}</style>
    </div>
  );
}

function ConfigureStep({ config, onChange, onNext, availableCorridors }) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const selectedRisk = RISK_APPETITE_MAP[config.riskAppetite];

  const totalLiquidity = availableCorridors
    .filter(c => config.corridorsIncluded.includes(c.code))
    .reduce((sum, c) => sum + (c.current_balance_musd || 0), 0);

  return (
    <div className="space-y-6">
      <div className="card p-5 space-y-6">
        
        {/* Corridor Selection */}
        <div>
          <label className="block text-[11px] uppercase tracking-wide text-muted font-mono mb-3">
            Select corridors to include in optimization:
          </label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {availableCorridors.map(c => (
              <label key={c.code} className="flex items-center gap-2 text-sm bg-surface/50 p-2.5 rounded-md border border-border cursor-pointer hover:border-teal/50 transition-colors">
                <input 
                  type="checkbox" 
                  checked={config.corridorsIncluded.includes(c.code)} 
                  onChange={(e) => {
                    if (e.target.checked) onChange({ ...config, corridorsIncluded: [...config.corridorsIncluded, c.code] });
                    else onChange({ ...config, corridorsIncluded: config.corridorsIncluded.filter(id => id !== c.code) });
                  }} 
                  className="accent-teal w-4 h-4 rounded-sm border-border bg-surface" 
                />
                <span className="font-mono">{c.code}</span>
              </label>
            ))}
          </div>
          <div className="mt-3 text-xs text-muted font-mono flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-teal"></span>
            {config.corridorsIncluded.length} corridors selected • Total liquidity in scope: ${totalLiquidity.toFixed(1)}M
          </div>
        </div>
      </div>

      <div className="card p-5 space-y-6">
        {/* Risk Appetite */}
        <div>
          <label className="block text-[11px] uppercase tracking-wide text-muted font-mono mb-3">
            How much settlement risk is acceptable?
          </label>
          <select 
            value={config.riskAppetite} 
            onChange={(e) => onChange({ ...config, riskAppetite: e.target.value })} 
            className="input md:w-1/2"
          >
            {Object.entries(RISK_APPETITE_MAP).map(([k, v]) => (
              <option key={k} value={k}>{v.label}</option>
            ))}
          </select>
          
          <div className="mt-4 p-4 rounded-md bg-surface/50 border border-teal/20">
            <div className="text-sm font-medium text-teal mb-2">
              {selectedRisk.label} strategy targets:
            </div>
            <ul className="text-sm text-muted space-y-1.5">
              <li className="flex items-center gap-2"><span className="text-faint">•</span> Coverage: {selectedRisk.confidence * 100}th percentile of historical demand</li>
              <li className="flex items-center gap-2"><span className="text-faint">•</span> Safety buffer: {selectedRisk.safetyBuffer * 100}% additional mathematical margin</li>
              <li className="flex items-center gap-2"><span className="text-faint">•</span> Expected capital release: <span className="text-gold font-medium">{selectedRisk.expectedRelease}</span></li>
            </ul>
          </div>
        </div>

        {/* Constraints */}
        <div>
          <label className="block text-[11px] uppercase tracking-wide text-muted font-mono mb-3">
            Global Liquidity Cap ($M)
          </label>
          <input 
            type="number" 
            placeholder="No limit (leave blank)" 
            value={config.globalCap} 
            onChange={(e) => onChange({ ...config, globalCap: e.target.value })} 
            className="input md:w-1/2" 
          />
          <p className="text-xs text-muted mt-1">Optional hard ceiling on total capital allocated across all included corridors.</p>
        </div>
      </div>

      <div className="card p-5">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-[11px] uppercase tracking-wide text-teal font-mono flex items-center gap-1 hover:text-teal/80 transition-colors"
        >
          {showAdvanced ? "▼ Hide Advanced Settings" : "▶ Show Advanced Settings"}
        </button>
        
        {showAdvanced && (
          <div className="mt-4 pt-4 border-t border-border/50">
            <p className="text-xs text-muted mb-4">
              These settings are pre-configured based on your risk appetite. Only modify if you understand the implications of simulated annealing parameters.
            </p>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Field label="Confidence level (Override)">
                <input type="number" step="0.01" value={selectedRisk.confidence} disabled className="input opacity-50 cursor-not-allowed" />
              </Field>
              <Field label="Iterations">
                <input type="number" value={config.iterations} onChange={(e) => onChange({...config, iterations: Number(e.target.value)})} className="input" />
              </Field>
              <Field label="Initial temp">
                <input type="number" value={config.initialTemperature} onChange={(e) => onChange({...config, initialTemperature: Number(e.target.value)})} className="input" />
              </Field>
              <Field label="Cooling rate">
                <input type="number" step="0.001" value={config.coolingRate} onChange={(e) => onChange({...config, coolingRate: Number(e.target.value)})} className="input" />
              </Field>
            </div>
          </div>
        )}
      </div>

      <div className="flex justify-end">
        <button
          onClick={onNext}
          disabled={config.corridorsIncluded.length === 0}
          className="bg-teal text-bg font-medium text-sm rounded-md px-6 py-2.5 hover:bg-teal/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Continue to Run →
        </button>
      </div>
    </div>
  );
}

function RunStep({ config, onComplete, onCancel }) {
  const [stage, setStage] = useState(0);
  const [error, setError] = useState(null);

  useEffect(() => {
    let stageTimer;
    let isCancelled = false;

    async function run() {
      stageTimer = setInterval(() => {
        setStage((s) => Math.min(s + 1, STAGES.length - 2));
      }, 220);

      try {
        const payload = {
          confidence_level: RISK_APPETITE_MAP[config.riskAppetite].confidence,
          iterations: config.iterations,
          initial_temperature: config.initialTemperature,
          cooling_rate: config.coolingRate,
          corridors: config.corridorsIncluded.length > 0 ? config.corridorsIncluded : undefined,
        };
        if (config.globalCap && !isNaN(Number(config.globalCap))) {
          payload.global_liquidity_cap_musd = Number(config.globalCap);
        }
        
        const res = await client.post("/api/optimization/run", payload);
        if (isCancelled) return;
        
        clearInterval(stageTimer);
        setStage(STAGES.length - 1);
        setTimeout(() => {
          if (!isCancelled) onComplete(res.data);
        }, 500);
      } catch (err) {
        if (isCancelled) return;
        clearInterval(stageTimer);
        setError(err.response?.data?.detail || "Optimization could not produce a valid solution.");
      }
    }
    
    run();
    
    return () => {
      isCancelled = true;
      clearInterval(stageTimer);
    };
  }, []);

  return (
    <div className="card p-8 max-w-2xl mx-auto mt-8">
      {error ? (
        <div className="space-y-4">
          <div className="text-red font-medium flex items-center gap-2">
            <span className="text-lg">⚠</span> Optimization Failed
          </div>
          <div className="text-sm text-muted bg-surface/50 p-4 border border-red/20 rounded-md">
            {error}
          </div>
          <button onClick={onCancel} className="text-sm px-4 py-2 rounded-md border border-border hover:bg-surface transition-colors">
            ← Back to Configuration
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="text-lg font-medium text-center">Processing Recommendation Model</div>
          <div className="space-y-3">
            {STAGES.map((s, i) => (
              <div key={s} className={`flex items-center gap-3 text-sm transition-all duration-300 ${i <= stage ? "text-text" : "text-faint opacity-50"}`}>
                <div className={`w-2 h-2 rounded-full flex-shrink-0 ${i < stage ? "bg-teal shadow-[0_0_8px_rgba(79,184,174,0.5)]" : i === stage ? "bg-gold animate-pulse shadow-[0_0_8px_rgba(199,162,76,0.5)]" : "bg-faint"}`} />
                <span>{s}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ReviewStep({ results, onStartOver }) {
  const [approvalStatus, setApprovalStatus] = useState(null);
  const [expandedCorridor, setExpandedCorridor] = useState(null);

  async function approve(decision) {
    await client.post("/api/optimization/approve", { run_id: results.run_id, decision });
    setApprovalStatus(decision);
  }

  const convergenceData = results.convergence_history?.map((e, i) => ({ step: i, energy: e })) || [];

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button onClick={onStartOver} className="text-xs uppercase tracking-wide text-muted font-mono hover:text-text transition-colors">
          ← Configure new run
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Kpi label="Current liquidity" value={`$${results.current_liquidity_musd.toFixed(1)}M`} />
        <Kpi label="Optimized liquidity" value={`$${results.optimized_liquidity_musd.toFixed(1)}M`} tone="teal" />
        <Kpi
          label="Capital released"
          value={`${results.capital_released_musd >= 0 ? "" : "-"}$${Math.abs(results.capital_released_musd).toFixed(1)}M`}
          tone={results.capital_released_musd >= 0 ? "gold" : "red"}
        />
        {results.global_liquidity_cap_musd ? (
          <Kpi 
            label="Capacity Utilized" 
            value={`${((results.optimized_liquidity_musd / results.global_liquidity_cap_musd) * 100).toFixed(1)}%`} 
            sub={`of $${results.global_liquidity_cap_musd}M cap`}
          />
        ) : (
          <Kpi label="QUBO energy" value={results.final_energy.toFixed(1)} sub={`from ${results.initial_energy.toFixed(0)}`} />
        )}
        <Kpi label="Variables" value={results.qubo_variables} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="Variables" value={results.qubo_variables} />
        <Kpi label="Non-zero terms" value={results.qubo_terms} />
        <Kpi label="Runtime" value={`${results.runtime_ms.toFixed(0)}ms`} />
        <Kpi
          label="Constraint satisfaction"
          value={results.constraint_violations.length === 0 ? "Clean" : `${results.constraint_violations.length} flagged`}
          tone={results.constraint_violations.length === 0 ? "teal" : "gold"}
        />
      </div>

      {results.constraint_violations.length > 0 && (
        <div className="card border-gold/30 p-3 space-y-1">
          {results.constraint_violations.map((v, i) => (
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
          <BarChart data={results.corridor_results.map((r) => ({ ...r, code: r.explanation.corridor_code }))}>
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
        {results.corridor_results.map((r) => {
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
