import React from 'react';

export default function Forecast() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Payment Demand Forecasting</h1>
        <p className="text-sm text-muted mt-1">Configuration for the Day-of-Week Seasonal Naive forecasting model.</p>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="card p-5">
          <h3 className="font-medium mb-1">Active Model</h3>
          <p className="text-sm text-muted mb-4">Seasonal Naive (Day-of-Week)</p>
          <div className="text-xs font-mono text-muted p-3 bg-subtle rounded border border-border">
            MAE: 0.3380<br/>
            Breach Rate: 1.9%
          </div>
        </div>
        <div className="card p-5">
          <h3 className="font-medium mb-1">Calibration</h3>
          <p className="text-sm text-muted mb-4">Gaussian Parametric (z=1.645)</p>
          <div className="text-xs font-mono text-muted p-3 bg-subtle rounded border border-border">
            Target Confidence: 95.0%<br/>
            Lookback: 90 Days
          </div>
        </div>
      </div>
    </div>
  );
}
