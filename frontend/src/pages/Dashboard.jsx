import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import client from "../api/client";
import { Kpi, Loading, ErrorState } from "../components/Common";
import { useQuantumStatus } from "../components/benchmark";

const BAR_COLORS = [
  "#4FB8AE",
  "#C7A24C",
  "#6E8FE0",
  "#D66B56",
  "#A78BFA",
  "#5B8DEF",
];

export default function Dashboard() {
  const [dash, setDash] = useState(null);
  const [corridors, setCorridors] = useState(null);
  const [savings, setSavings] = useState(null);
  const [error, setError] = useState(null);
  
  const quantum = useQuantumStatus();

  async function load() {
    setError(null);
    try {
      const [d, c, s] = await Promise.all([
        client.get("/api/dashboard"),
        client.get("/api/corridors"),
        client.get("/api/dashboard/savings")
      ]);
      setDash(d.data);
      setCorridors(c.data);
      setSavings(s.data);
    } catch (err) {
      setError("Could not load dashboard data.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!dash || !corridors || !savings) return <Loading label="Loading dashboard" />;

  const currencyData = Object.entries(dash.liquidity_by_currency_musd).map(
    ([k, v]) => ({ currency: k, value: v }),
  );

  const opportunityCostRate = savings.opportunityCostRate;
  const isEstimate = !dash.latest_optimization_run;
  const capitalReleased = dash.capital_released_potential_musd;
  const totalNostroLiquidity = dash.total_nostro_liquidity_musd;
  const annualSavingsOpportunity = savings.annualSavingsOpportunity;
  const efficiencyImprovement = savings.efficiencyImprovement;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-semibold">
          {dash.organization}
        </h1>
        <div className={`px-3 py-1 rounded-full text-xs font-medium border flex items-center gap-2 ${
            quantum.status === "online" 
              ? "bg-green-500/20 text-green-400 border-green-500/30" 
              : "bg-amber-500/20 text-amber-400 border-amber-500/30"
          }`}>
            <span className={`w-2 h-2 rounded-full ${quantum.status === 'online' ? 'bg-green-400 animate-pulse' : 'bg-amber-400'}`}></span>
            {quantum.status === 'online' ? 'Quantum Core Online' : 'Quantum Core Offline'}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Kpi
          label="Total nostro liquidity"
          value={`$${totalNostroLiquidity.toFixed(1)}M`}
        />
        <Kpi label="Corridors" value={dash.num_corridors} />
        <Kpi
          label="Capital Released (Optimized)"
          value={`$${capitalReleased.toFixed(1)}M`}
          tone={capitalReleased >= 0 ? "gold" : "red"}
        />
        {dash.latest_optimization_run ? (
          <Kpi label="Nostro accounts" value={dash.num_nostro_accounts} />
        ) : (
          <div className="card px-4 py-3.5 flex flex-col justify-between">
            <div className="text-[11px] uppercase tracking-wide text-muted font-mono">
              Optimization
            </div>
            <Link
              to="/optimizer"
              className="text-teal text-sm font-medium hover:underline"
            >
              Run optimizer &rarr;
            </Link>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-2 gap-3">
        <Kpi
          label={
            isEstimate
              ? `Annual Savings Opportunity (${opportunityCostRate * 100}% rate)`
              : `Annual Savings (${opportunityCostRate * 100}% rate)`
          }
          value={`$${annualSavingsOpportunity.toFixed(2)}M`}
          tone="teal"
        />
        <Kpi
          label={
            isEstimate
              ? "Efficiency Improvement potential"
              : "Efficiency Improvement"
          }
          value={`+${efficiencyImprovement.toFixed(1)}%`}
          tone="teal"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-4">
          <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-3">
            Liquidity by currency ($M)
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={currencyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#263041" />
              <XAxis dataKey="currency" stroke="#7C8AA0" fontSize={12} />
              <YAxis stroke="#7C8AA0" fontSize={12} />
              <Tooltip
                cursor={{ fill: "#1f2937" }}
                contentStyle={{
                  background: "#171E27",
                  border: "1px solid #263041",
                  fontSize: 12,
                }}
              />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {currencyData.map((_, i) => (
                  <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        
        <div className="card p-4">
          <div className="text-[11px] uppercase tracking-wide text-muted font-mono mb-3">
            Capital Release Opportunity by Corridor ($M)
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart 
              data={corridors.map(c => ({
                code: c.code, 
                opportunity: Math.max(0, (c.current_balance_musd || 0) - (c.recommended_musd || 0))
              })).sort((a,b) => b.opportunity - a.opportunity)} 
              layout="vertical" 
              margin={{ left: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#263041" />
              <XAxis type="number" stroke="#7C8AA0" fontSize={12} />
              <YAxis
                type="category"
                dataKey="code"
                stroke="#7C8AA0"
                fontSize={11}
                width={70}
              />
              <Tooltip
                cursor={{ fill: "#1f2937" }}
                contentStyle={{
                  background: "#171E27",
                  border: "1px solid #263041",
                  fontSize: 12,
                }}
              />
              <Bar
                dataKey="opportunity"
                radius={[0, 4, 4, 0]}
              >
                {corridors.map((c, i) => (
                  <Cell key={i} fill="#C7A24C" />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

      </div>
    </div>
  );
}
