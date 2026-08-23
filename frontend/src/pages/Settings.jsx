import React from 'react';

export default function Settings() {
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
            <input type="range" min="90" max="99" defaultValue="95" className="w-full accent-primary" />
            <span className="font-mono text-sm">95%</span>
          </div>
          <p className="text-xs text-muted mt-1">Governs the Gaussian safety buffer multiplier.</p>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Opportunity Cost Rate</label>
          <div className="flex gap-4 items-center">
            <input type="range" min="1" max="10" defaultValue="5" className="w-full accent-primary" />
            <span className="font-mono text-sm">5.0%</span>
          </div>
          <p className="text-xs text-muted mt-1">Blended annual yield assumption for released capital.</p>
        </div>
      </div>
    </div>
  );
}
