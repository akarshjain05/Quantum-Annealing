import { Fragment, useEffect, useState } from "react";
import client from "../api/client";
import { Loading, ErrorState } from "../components/Common";
import SettlementTimeline from "../components/SettlementTimeline";

export default function Corridors() {
  const [corridors, setCorridors] = useState(null);
  const [forecasts, setForecasts] = useState({});
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(null);

  async function load() {
    setError(null);
    try {
      const res = await client.get("/api/corridors");
      setCorridors(res.data);
    } catch {
      setError("Could not load corridors.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function toggleExpand(code) {
    if (expanded === code) {
      setExpanded(null);
      return;
    }
    setExpanded(code);
    if (!forecasts[code]) {
      const res = await client.get(`/api/forecasts/${code}`);
      setForecasts((f) => ({ ...f, [code]: res.data }));
    }
  }

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!corridors) return <Loading label="Loading corridors" />;


  // Sort by opportunity size (current - recommended) biggest first
  const sortedCorridors = [...corridors].sort((a, b) => {
    const oppA = (a.current_balance_musd || 0) - (a.recommended_musd || 0);
    const oppB = (b.current_balance_musd || 0) - (b.recommended_musd || 0);
    return oppB - oppA;
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Corridors</h1>
        <p className="text-sm text-muted mt-1">
          {corridors.length} active corridors across {new Set(corridors.flatMap(c => [c.source_currency, c.dest_currency])).size} currencies.
        </p>
      </div>

      <SettlementTimeline corridors={corridors} />

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted font-mono">
              <th className="px-4 py-2.5">Corridor</th>
              <th className="px-4 py-2.5">Pair</th>
              <th className="px-4 py-2.5 text-right">Balance ($M)</th>
              <th className="px-4 py-2.5 text-right">Recommended ($M)</th>
              <th className="px-4 py-2.5 text-right">Efficiency</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5 text-right">Cut-off (UTC)</th>
              <th className="px-4 py-2.5 text-right">Window (UTC)</th>
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {sortedCorridors.map((c) => (
              <Fragment key={c.code}>
                <tr
                  className="border-b border-border/60 hover:bg-raised/40 cursor-pointer transition-colors"
                  onClick={() => toggleExpand(c.code)}
                >
                  <td className="px-4 py-2.5 font-mono">{c.code}</td>
                  <td className="px-4 py-2.5 text-muted">{c.name}</td>
                  <td className="px-4 py-2.5 text-right font-mono">
                    ${c.current_balance_musd.toFixed(1)}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-teal">
                    ${c.recommended_musd?.toFixed(1) || "--"}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono">
                    <span
                      className={`px-1.5 py-0.5 rounded text-xs ${c.efficiency_pct < 75 ? "bg-red/20 text-red" : c.efficiency_pct < 90 ? "bg-gold/20 text-gold" : "bg-teal/20 text-teal"}`}
                    >
                      {c.efficiency_pct.toFixed(1)}%
                    </span>
                  </td>

                  <td className="px-4 py-2.5 text-right font-mono text-muted">
                    {c.cutoff_hour_utc}:00
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono text-muted">
                    {c.settlement_window_utc[0]}:00-{c.settlement_window_utc[1]}
                    :00
                  </td>
                  <td className="px-4 py-2.5 text-right text-teal text-xs">
                    {expanded === c.code ? "hide" : "forecast"}
                  </td>
                </tr>
                {expanded === c.code && (
                  <tr className="bg-surface/50 border-b border-border">
                    <td colSpan={8} className="px-6 py-6">
                      {forecasts[c.code] ? (
                        (() => {
                          const fc = forecasts[c.code];

                          const targetRecommended = c.recommended_musd;

                          const expected7d = fc.expected_demand_musd;
                          const base_demand = fc.ci_high_musd;
                          const peakBuffer = Math.max(0, base_demand - expected7d);

                          const settlementBuffer = base_demand * 0.05;
                          const fxReserve = base_demand * 0.075;
                          const correspondentMargin = base_demand * 0.02;

                          const minimumRequired =
                            base_demand +
                            settlementBuffer +
                            fxReserve +
                            correspondentMargin;
                          const recommendedMin = targetRecommended; 
                          const recommendationBuffer =
                            Math.max(0, recommendedMin - minimumRequired);

                          const currentBal = c.current_balance_musd;
                          const excess = Math.max(0, currentBal - recommendedMin);
                          const coverageRatio =
                            recommendedMin > 0 ? (currentBal / recommendedMin) * 100 : 100;

                          return (
                            <div className="space-y-6">
                              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                <div>
                                  <div className="text-muted text-[11px] uppercase tracking-wide font-mono mb-1">
                                    Coverage Ratio
                                  </div>
                                  <div
                                    className={`font-display text-2xl font-semibold tabular ${coverageRatio >= 100 ? "text-teal" : "text-gold"}`}
                                  >
                                    {coverageRatio.toFixed(1)}%
                                  </div>
                                  <div className="text-xs text-muted mt-1">
                                    {coverageRatio >= 100
                                      ? "Above safety level ✓"
                                      : "⚠️ Below target"}
                                  </div>
                                </div>
                                <div>
                                  <div className="text-muted text-[11px] uppercase tracking-wide font-mono mb-1">
                                    7d Expected Demand
                                  </div>
                                  <div className="font-mono tabular text-text text-lg">
                                    ${fc.expected_demand_musd.toFixed(2)}M
                                  </div>
                                </div>
                                <div>
                                  <div className="text-muted text-[11px] uppercase tracking-wide font-mono mb-1">
                                    95% CI Limit
                                  </div>
                                  <div className="font-mono tabular text-text text-lg">
                                    ${fc.ci_high_musd.toFixed(1)}M
                                  </div>
                                </div>
                                <div>
                                  <div className="text-muted text-[11px] uppercase tracking-wide font-mono mb-1">
                                    Txns (90d)
                                  </div>
                                  <div className="font-mono tabular text-text text-lg">
                                    {fc.transaction_count_90d}
                                  </div>
                                </div>
                              </div>

                              <div className="border border-border rounded-md overflow-hidden bg-bg">
                                <div className="px-4 py-2 border-b border-border bg-surface text-[11px] uppercase tracking-wide text-muted font-mono">
                                  Recommendation Breakdown
                                </div>
                                <table className="w-full text-sm">
                                  <thead className="bg-surface/50 text-[11px] text-muted font-mono border-b border-border text-left">
                                    <tr>
                                      <th className="px-4 py-2 font-normal">
                                        Component
                                      </th>
                                      <th className="px-4 py-2 font-normal text-right">
                                        Amount
                                      </th>
                                      <th className="px-4 py-2 font-normal">
                                        Basis
                                      </th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-border/50">
                                    <tr>
                                      <td className="px-4 py-2">
                                        Expected 7-Day Demand
                                      </td>
                                      <td className="px-4 py-2 text-right font-mono">
                                        ${expected7d.toFixed(1)}M
                                      </td>
                                      <td className="px-4 py-2 text-muted text-xs">
                                        7-day historical forecast
                                      </td>
                                    </tr>
                                    <tr>
                                      <td className="px-4 py-2">
                                        Peak Demand Buffer (95th %ile)
                                      </td>
                                      <td className="px-4 py-2 text-right font-mono">
                                        ${peakBuffer.toFixed(1)}M
                                      </td>
                                      <td className="px-4 py-2 text-muted text-xs">
                                        Historical peaks margin
                                      </td>
                                    </tr>
                                    <tr>
                                      <td className="px-4 py-2">
                                        Settlement Risk Buffer
                                      </td>
                                      <td className="px-4 py-2 text-right font-mono">
                                        ${settlementBuffer.toFixed(1)}M
                                      </td>
                                      <td className="px-4 py-2 text-muted text-xs">
                                        5% of P95 Demand
                                      </td>
                                    </tr>
                                    <tr>
                                      <td className="px-4 py-2">
                                        FX Volatility Reserve
                                      </td>
                                      <td className="px-4 py-2 text-right font-mono">
                                        ${fxReserve.toFixed(1)}M
                                      </td>
                                      <td className="px-4 py-2 text-muted text-xs">
                                        7.5% of P95 Demand (volatility proxy)
                                      </td>
                                    </tr>
                                    <tr>
                                      <td className="px-4 py-2">
                                        Correspondent Risk Margin
                                      </td>
                                      <td className="px-4 py-2 text-right font-mono">
                                        ${correspondentMargin.toFixed(1)}M
                                      </td>
                                      <td className="px-4 py-2 text-muted text-xs">
                                        2% of P95 (A- rating)
                                      </td>
                                    </tr>
                                    <tr>
                                      <td className="px-4 py-2">
                                        + Discretization & Final Buffer
                                      </td>
                                      <td className="px-4 py-2 text-right font-mono">
                                        ${recommendationBuffer.toFixed(1)}M
                                      </td>
                                      <td className="px-4 py-2 text-muted text-xs">
                                        Rounding up to nearest Quantum Engine Bucket
                                      </td>
                                    </tr>
                                    <tr className="bg-surface/50 font-medium">
                                      <td className="px-4 py-2.5 text-teal">
                                        RECOMMENDED MINIMUM
                                      </td>
                                      <td className="px-4 py-2.5 text-right font-mono text-teal">
                                        ${recommendedMin.toFixed(1)}M
                                      </td>
                                      <td className="px-4 py-2.5"></td>
                                    </tr>
                                    <tr>
                                      <td className="px-4 py-2.5">
                                        Current Balance
                                      </td>
                                      <td className="px-4 py-2.5 text-right font-mono">
                                        ${currentBal.toFixed(1)}M
                                      </td>
                                      <td className="px-4 py-2.5"></td>
                                    </tr>
                                    <tr className="bg-gold/5 font-medium">
                                      <td className="px-4 py-2.5 text-gold">
                                        EXCESS CAPITAL
                                      </td>
                                      <td className="px-4 py-2.5 text-right font-mono text-gold">
                                        ${excess.toFixed(1)}M
                                      </td>
                                      <td className="px-4 py-2.5 text-gold text-xs">
                                        Available for release
                                      </td>
                                    </tr>
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          );
                        })()
                      ) : (
                        <div className="flex items-center gap-2 text-muted text-sm py-4">
                          <span className="inline-block w-3 h-3 rounded-full border-2 border-teal border-t-transparent animate-spin" />
                          Analyzing corridor data...
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
