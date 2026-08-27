import React, { useState, useEffect } from 'react';

export default function Settings() {
  const [confidence, setConfidence] = useState(95);
  const [costRate, setCostRate] = useState(5.0);

  useEffect(() => {
    const savedConf = localStorage.getItem('targetConfidence');
    const savedCost = localStorage.getItem('opportunityCostRate');
    if (savedConf) setConfidence(Number(savedConf));
    if (savedCost) setCostRate(Number(savedCost));
  }, []);

  const handleConfChange = (e) => {
    const val = Number(e.target.value);
    setConfidence(val);
    localStorage.setItem('targetConfidence', val);
  };

  const handleCostChange = (e) => {
    const val = Number(e.target.value);
    setCostRate(val);
    localStorage.setItem('opportunityCostRate', val);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-semibold">Treasury Parameters</h1>
        <p className="text-sm text-muted mt-1">Global risk appetite and operational settings.</p>
      </div>
      <div className="card p-6 space-y-6 max-w-2xl">
        <div>
          <label className="block text-sm font-medium mb-1">Target Confidence Level</label>
          <div className="flex gap-4 items-center">
            <input type="range" min="90" max="99" value={confidence} onChange={handleConfChange} className="w-full accent-primary" />
            <span className="font-mono text-sm">{confidence}%</span>
          </div>
          <p className="text-xs text-muted mt-1">Governs the Gaussian safety buffer multiplier.</p>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Opportunity Cost Rate</label>
          <div className="flex gap-4 items-center">
            <input type="range" min="1" max="10" step="0.1" value={costRate} onChange={handleCostChange} className="w-full accent-primary" />
            <span className="font-mono text-sm">{costRate.toFixed(1)}%</span>
          </div>
          <p className="text-xs text-muted mt-1">Blended annual yield assumption for released capital.</p>
        </div>
      </div>
    </div>
  );
}
