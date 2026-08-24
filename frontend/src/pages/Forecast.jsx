import React, { useEffect, useState } from 'react';
import client from '../api/client';
import { EmptyState, Loading } from '../components/Common';

export default function Forecast() {
  const [corridors, setCorridors] = useState([]);
  const [selectedCorridor, setSelectedCorridor] = useState("");
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    client.get("/api/corridors")
      .then(res => {
        setCorridors(res.data);
        if (res.data.length > 0) {
          setSelectedCorridor(res.data[0].code);
        }
      })
      .catch(err => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedCorridor) return;
    setForecast(null);
    client.get(`/api/forecasts/${selectedCorridor}?horizon_days=7`)
      .then(res => setForecast(res.data))
      .catch(err => console.error(err));
  }, [selectedCorridor]);

  if (loading) return <Loading label="Loading forecast configuration" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Payment Demand Forecasting</h1>
        <p className="text-sm text-muted mt-1">Configuration for the Day-of-Week Seasonal Naive forecasting model.</p>
      </div>

      {corridors.length === 0 ? (
        <EmptyState title="No Corridors" hint="Add corridors to view forecasts." />
      ) : (
        <>
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium">Select Corridor:</span>
            <select 
              value={selectedCorridor} 
              onChange={e => setSelectedCorridor(e.target.value)}
              className="px-3 py-2 bg-surface border border-border rounded text-sm"
            >
              {corridors.map(c => <option key={c.code} value={c.code}>{c.code}</option>)}
            </select>
          </div>

          {!forecast ? <Loading label="Computing forecast" /> : (
            <div className="grid grid-cols-2 gap-4">
              <div className="card p-5">
                <h3 className="font-medium mb-1">Active Model</h3>
                <p className="text-sm text-muted mb-4">{forecast.model_used}</p>
                <div className="text-xs font-mono text-muted p-3 bg-subtle rounded border border-border space-y-1">
                  <div>Expected 7-Day Demand: <span className="text-primary">${forecast.expected_demand_musd.toFixed(2)}M</span></div>
                  <div>Volatility (Std Dev): <span className="text-primary">${forecast.std_dev_musd.toFixed(2)}M</span></div>
                  <div>95% CI Range: <span className="text-primary">${forecast.ci_low_musd.toFixed(2)}M - ${forecast.ci_high_musd.toFixed(2)}M</span></div>
                </div>
              </div>
              <div className="card p-5">
                <h3 className="font-medium mb-1">Calibration</h3>
                <p className="text-sm text-muted mb-4">Historical Transactions ({forecast.horizon_days} Day Horizon)</p>
                <div className="text-xs font-mono text-muted p-3 bg-subtle rounded border border-border space-y-1">
                  <div>Lookback History: <span className="text-primary">90 Days</span></div>
                  <div>Sample Size: <span className="text-primary">{forecast.transaction_count_90d} transactions</span></div>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
