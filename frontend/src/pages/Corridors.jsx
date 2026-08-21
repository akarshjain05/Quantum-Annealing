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

  useEffect(() => { load(); }, []);

  async function toggleExpand(code) {
    if (expanded === code) { setExpanded(null); return; }
    setExpanded(code);
    if (!forecasts[code]) {
      const res = await client.get(`/api/forecasts/${code}`);
      setForecasts((f) => ({ ...f, [code]: res.data }));
    }
  }

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!corridors) return <Loading label="Loading corridors" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Corridors</h1>
        <p className="text-sm text-muted mt-1">{corridors.length} synthetic demo corridors across 8 currencies.</p>
      </div>

      <SettlementTimeline corridors={corridors} />

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-[11px] uppercase tracking-wide text-muted font-mono">
              <th className="px-4 py-2.5">Corridor</th>
              <th className="px-4 py-2.5">Pair</th>
              <th className="px-4 py-2.5 text-right">Balance ($M)</th>
              <th className="px-4 py-2.5 text-right">Cut-off (UTC)</th>
              <th className="px-4 py-2.5 text-right">Window (UTC)</th>
              <th className="px-4 py-2.5" />
            </tr>
          </thead>
          <tbody>
            {corridors.map((c) => (
              <Fragment key={c.code}>
                <tr
                  className="border-b border-border/60 hover:bg-raised/40 cursor-pointer transition-colors"
                  onClick={() => toggleExpand(c.code)}
                >
                  <td className="px-4 py-2.5 font-mono">{c.code}</td>
                  <td className="px-4 py-2.5 text-muted">{c.name}</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular">{c.current_balance_musd.toFixed(2)}</td>
                  <td className="px-4 py-2.5 text-right font-mono text-muted">{c.cutoff_hour_utc}:00</td>
                  <td className="px-4 py-2.5 text-right font-mono text-muted">{c.settlement_window_utc[0]}:00-{c.settlement_window_utc[1]}:00</td>
                  <td className="px-4 py-2.5 text-right text-teal text-xs">{expanded === c.code ? "hide" : "forecast"}</td>
                </tr>
                {expanded === c.code && (
                  <tr className="bg-raised/30">
                    <td colSpan={6} className="px-4 py-3">
                      {forecasts[c.code] ? (
                        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
                          <div><div className="text-muted">7d expected demand</div><div className="font-mono tabular text-text">${forecasts[c.code].expected_demand_musd.toFixed(2)}M</div></div>
                          <div><div className="text-muted">Std dev</div><div className="font-mono tabular text-text">${forecasts[c.code].std_dev_musd.toFixed(2)}M</div></div>
                          <div><div className="text-muted">95% CI</div><div className="font-mono tabular text-text">${forecasts[c.code].ci_low_musd.toFixed(1)}-${forecasts[c.code].ci_high_musd.toFixed(1)}M</div></div>
                          <div><div className="text-muted">Model</div><div className="font-mono text-text text-[11px]">{forecasts[c.code].model_used}</div></div>
                          <div><div className="text-muted">Txns (90d)</div><div className="font-mono tabular text-text">{forecasts[c.code].transaction_count_90d}</div></div>
                        </div>
                      ) : <div className="text-muted text-xs">Loading forecast...</div>}
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
