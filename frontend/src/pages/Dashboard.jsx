import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import client from "../api/client";
import { Kpi, Loading, ErrorState } from "../components/Common";
import SettlementTimeline from "../components/SettlementTimeline";

const BAR_COLORS = ["#4FB8AE", "#C7A24C", "#6E8FE0", "#D66B56", "#A78BFA", "#5B8DEF"];

export default function Dashboard() {
  const [dash, setDash] = useState(null);
  const [corridors, setCorridors] = useState(null);
  const [error, setError] = useState(null);

  async function load() {
    setError(null);
    try {
      const [d, c] = await Promise.all([
        client.get("/api/dashboard"),
        client.get("/api/corridors"),
      ]);
      setDash(d.data);
      setCorridors(c.data);
    } catch (err) {
      setError("Could not load dashboard data.");
    }
  }

  useEffect(() => { load(); }, []);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!dash || !corridors) return <Loading label="Loading dashboard" />;

  const currencyData = Object.entries(dash.liquidity_by_currency_musd).map(([k, v]) => ({ currency: k, value: v }));

  const opportunityCostRate = 0.05;
  
  const isEstimate = !dash.latest_optimization_run;
  const capitalReleased = isEstimate 
    ? dash.capital_released_potential_musd 
    : dash.latest_optimization_run.capital_released_musd;
    
  const totalNostroLiquidity = dash.total_nostro_liquidity_musd;
  const annualSavingsOpportunity = capitalReleased * opportunityCostRate;
  const efficiencyImprovement = totalNostroLiquidity > 0 ? (capitalReleased / totalNostroLiquidity) * 100 : 0;
  const operatingMode = 'shadow';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">{dash.organization}</h1>
        <p className="text-sm text-muted mt-1">{dash.synthetic_data_notice}</p>
      </div>

      {/* NEW: Operating Mode Banner */}
      <div className="card p-3 bg-surface/50 border border-teal/20 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-2 h-2 rounded-full bg-teal animate-pulse"></div>
          <span className="text-sm font-medium text-teal">
            {operatingMode === 'shadow' 
              ? 'SHADOW MODE - Recommendations only, no live execution' 
              : 'PRODUCTION MODE - Live recommendations enabled'}
          </span>
        </div>
        <span className="text-xs text-muted hover:text-teal transition-colors cursor-pointer">
          Learn more
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi label="Total nostro liquidity" value={`$${totalNostroLiquidity.toFixed(1)}M`} />
        <Kpi label="Corridors" value={dash.num_corridors} />
        <Kpi 
          label={isEstimate ? "Capital Released potential" : "Capital released (latest run)"}
          value={`$${capitalReleased.toFixed(1)}M`}
          tone={capitalReleased >= 0 ? "gold" : "red"}
        />
        {dash.latest_optimization_run ? (
          <Kpi label="Nostro accounts" value={dash.num_nostro_accounts} />
        ) : (
          <div className="card px-4 py-3.5 flex flex-col justify-between">
            <div className="text-[11px] uppercase tracking-wide text-muted font-mono">Optimization</div>
            <Link to="/optimizer" className="text-teal text-sm font-medium hover:underline">Run optimizer &rarr;</Link>
          </div>
        )}
      </div>

      {/* NEW: Business Value Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-2 gap-3">
        <Kpi
          label={isEstimate ? "Annual Savings Opportunity" : "Annual Savings (5% rate)"}
          value={`$${annualSavingsOpportunity.toFixed(2)}M`}
          tone="teal"
        />
        <Kpi
          label={isEstimate ? "Efficiency Improvement potential" : "Efficiency Improvement"}
          value={`+${efficiencyImprovement.toFixed(1)}%`}
          tone="teal"
        />
      </div>

      <SettlementTimeline corridors={corridors} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-4">
          <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-3">Liquidity by currency ($M)</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={currencyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#263041" />
              <XAxis dataKey="currency" stroke="#7C8AA0" fontSize={12} />
              <YAxis stroke="#7C8AA0" fontSize={12} />
              <Tooltip cursor={{ fill: "#1f2937" }} contentStyle={{ background: "#171E27", border: "1px solid #263041", fontSize: 12 }} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {currencyData.map((_, i) => <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-4">
          <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-3">Current balance by corridor ($M)</div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={corridors} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#263041" />
              <XAxis type="number" stroke="#7C8AA0" fontSize={12} />
              <YAxis type="category" dataKey="code" stroke="#7C8AA0" fontSize={11} width={70} />
              <Tooltip cursor={{ fill: "#1f2937" }} contentStyle={{ background: "#171E27", border: "1px solid #263041", fontSize: 12 }} />
              <Bar dataKey="current_balance_musd" fill="#4FB8AE" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
