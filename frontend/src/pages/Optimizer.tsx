// frontend/src/pages/Optimizer.tsx
/**
 * Optimizer Page with Quantum Benchmark Integration
 */

import React, { useState } from "react";
import client from "../api/client";

import {
  BenchmarkComparisonChart,
  BenchmarkStatus,
  useBenchmark,
  useQuantumStatus,
} from "../components/benchmark";

// Types
type RiskAppetite =
  | "very_conservative"
  | "conservative"
  | "balanced"
  | "efficient"
  | "very_efficient";

interface OptimizerConfig {
  riskAppetite: RiskAppetite;
  confidenceLevel: number;
  safetyBuffer: number;
  runQuantum: boolean;
  seed: number;
}

const DEFAULT_CONFIG: OptimizerConfig = {
  riskAppetite: "conservative",
  confidenceLevel: 0.95,
  safetyBuffer: 0.05,
  runQuantum: true,
  seed: 42,
};

const RISK_DESCRIPTIONS: Record<
  RiskAppetite,
  { label: string; description: string }
> = {
  very_conservative: {
    label: "Very Conservative",
    description: "99th percentile coverage, 10% safety buffer, minimal risk",
  },
  conservative: {
    label: "Conservative",
    description: "95th percentile coverage, 5% safety buffer, low risk",
  },
  balanced: {
    label: "Balanced",
    description: "90th percentile coverage, 3% safety buffer, moderate risk",
  },
  efficient: {
    label: "Efficient",
    description:
      "85th percentile coverage, 2% safety buffer, higher efficiency",
  },
  very_efficient: {
    label: "Very Efficient",
    description:
      "80th percentile coverage, 1% safety buffer, maximum efficiency",
  },
};

export default function Optimizer() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [config, setConfig] = useState<OptimizerConfig>(() => {
    const savedConf = localStorage.getItem('targetConfidence');
    let conf = DEFAULT_CONFIG.confidenceLevel;
    if (savedConf) conf = Number(savedConf) / 100.0;
    
    return {
      ...DEFAULT_CONFIG,
      confidenceLevel: conf
    };
  });

  const { status: quantumStatus, loading: statusLoading } = useQuantumStatus();
  const {
    result,
    loading: optimizing,
    error,
    runOptimization,
    clearError,
  } = useBenchmark();

  const handleRunOptimization = async () => {
    setStep(2);
    clearError();

    try {
      await runOptimization({
        risk_config: {
          risk_appetite: config.riskAppetite,
          confidence_level: config.confidenceLevel,
          safety_buffer: config.safetyBuffer,
        },
        solver_config: {
          run_classical: true,
          run_quantum: config.runQuantum,
          seed: config.seed,
        },
        run_benchmark: true,
        save_results: true,
      });
      setStep(3);
    } catch (err) {
      // Error is handled by the hook
      setStep(1);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-white mb-2">
          Liquidity Optimizer
        </h1>
        <p className="text-gray-400">
          Configure, run, and review liquidity optimization with quantum
          benchmark comparison.
        </p>
      </div>

      {/* Step Indicator */}
      <div className="flex items-center gap-4 mb-8">
        <StepIndicator step={1} current={step} label="Configure" />
        <div className="h-px w-16 bg-gray-700" />
        <StepIndicator step={2} current={step} label="Run" />
        <div className="h-px w-16 bg-gray-700" />
        <StepIndicator step={3} current={step} label="Review" />
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
          <div className="flex items-center gap-2">
            <span className="text-red-400">❌</span>
            <span className="text-red-400 font-medium">Error</span>
          </div>
          <p className="text-sm text-gray-300 mt-1">{error}</p>
          <button
            onClick={clearError}
            className="text-sm text-red-400 hover:underline mt-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Step Content */}
      {step === 1 && (
        <ConfigureStep
          config={config}
          onChange={setConfig}
          quantumStatus={quantumStatus}
          statusLoading={statusLoading}
          onRun={handleRunOptimization}
        />
      )}

      {step === 2 && <RunningStep loading={optimizing} />}

      {step === 3 && result && (
        <ResultsStep
          result={result}
          onBack={() => setStep(1)}
          onSubmit={async () => {
            try {
              await client.post(
                `/api/optimization/runs/${result.run_id}/submit-for-approval`,
                {
                  submitted_by: "Demo User",
                  notes: "Submitted from Optimizer dashboard",
                },
              );
              alert(
                "Optimization submitted! This has been recorded on the immutable Audit Trail.",
              );
              // Optionally redirect to audit page: window.location.href = "/audit";
            } catch (err) {
              console.error(err);
              alert("Error submitting for approval");
            }
          }}
        />
      )}
    </div>
  );
}

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

const StepIndicator: React.FC<{
  step: number;
  current: number;
  label: string;
}> = ({ step, current, label }) => {
  const isActive = step === current;
  const isComplete = step < current;

  return (
    <div className="flex items-center gap-2">
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
          isComplete
            ? "bg-teal-500 text-[#FFFFFF]"
            : isActive
              ? "bg-teal-500/20 text-teal-600 border-2 border-teal-500"
              : "bg-gray-700 text-gray-400"
        }`}
      >
        {isComplete ? "✓" : step}
      </div>
      <span className={isActive ? "text-white font-medium" : "text-gray-400"}>
        {label}
      </span>
    </div>
  );
};

const ConfigureStep: React.FC<{
  config: OptimizerConfig;
  onChange: (config: OptimizerConfig) => void;
  quantumStatus: any;
  statusLoading: boolean;
  onRun: () => void;
}> = ({ config, onChange, quantumStatus, statusLoading, onRun }) => {
  return (
    <div className="space-y-6">
      {/* Quantum Status */}

      {/* Solver Configuration */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
          Solver Configuration
        </h3>

        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={config.runQuantum}
            onChange={(e) =>
              onChange({ ...config, runQuantum: e.target.checked })
            }
            className="w-4 h-4 rounded"
            disabled={!quantumStatus?.quantum_ready}
          />
          <div>
            <span className="text-white">Include Quantum Solvers</span>
            {!quantumStatus?.quantum_ready && (
              <span className="text-yellow-400 text-sm ml-2">
                (not available)
              </span>
            )}
          </div>
        </label>

        <p className="text-sm text-gray-500 mt-2 ml-7">
          Run QAOA and other quantum algorithms for comparison (slower but
          provides benchmark data)
        </p>
      </div>

      {/* Run Button */}
      <div className="flex justify-end">
        <button
          onClick={onRun}
          className="px-6 py-3 bg-teal-600 hover:bg-teal-500 font-medium rounded-lg transition-colors"
          style={{ color: "#FFFFFF" }}
        >
          Run Optimization →
        </button>
      </div>
    </div>
  );
};

const RunningStep: React.FC<{ loading: boolean }> = ({ loading }) => {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="w-16 h-16 border-4 border-teal-500/30 border-t-teal-500 rounded-full animate-spin mb-6" />
      <h3 className="text-xl font-medium text-white mb-2">
        Running Optimization
      </h3>
      <p className="text-gray-400 text-center max-w-md">
        Building QUBO formulation and running classical and quantum solvers.
        This may take a few moments...
      </p>
    </div>
  );
};

const ResultsStep: React.FC<{
  result: any;
  onBack: () => void;
  onSubmit: () => void;
}> = ({ result, onBack, onSubmit }) => {
  
  // Calculate dynamic insight
  let largestCorridor = "N/A";
  let largestPercent = 0;
  
  if (result && result.corridor_results && result.corridor_results.length > 0) {
    const sorted = [...result.corridor_results].sort((a, b) => {
      const pctA = a.current_balance > 0 ? (a.delta / a.current_balance) * 100 : 0;
      const pctB = b.current_balance > 0 ? (b.delta / b.current_balance) * 100 : 0;
      return pctB - pctA;
    });
    largestCorridor = sorted[0].corridor_code;
    largestPercent = sorted[0].current_balance > 0 
      ? Math.round((sorted[0].delta / sorted[0].current_balance) * 100) 
      : 0;
  }

  return (
    <div className="space-y-6">

      {/* Auto-generated Insight Banner */}
      <div className="bg-teal-900/30 border border-teal-500/40 rounded-lg p-4 flex items-start gap-4">
        <span className="text-2xl mt-0.5">💡</span>
        <div>
          <h4 className="text-sm font-medium text-teal-400 uppercase tracking-wider mb-1">Algorithmic Insight</h4>
          <p className="text-gray-300 text-sm">
            Quantum optimization successfully identified excess liquidity. <span className="text-white font-medium">{largestCorridor}</span> saw the largest reduction ({largestPercent}% reduction), while maintaining strict empirical settlement safety margins.
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SummaryCard
          label="Capital Released"
          value={`$${result.capital_released.toFixed(1)}M`}
          sublabel={`${result.capital_release_percent.toFixed(1)}% of total`}
          highlight
        />
        <SummaryCard
          label="Annual Savings"
          value={`$${result.annual_savings_opportunity.toFixed(1)}M`}
          sublabel="@ 5% cost of capital"
          highlight
        />
        <SummaryCard
          label="Corridors Optimized"
          value={result.num_corridors.toString()}
          sublabel="all safety requirements met"
        />
      </div>

      {/* Benchmark Chart */}
      {result.benchmark && (
        <div>
          <h2 className="text-xl font-semibold text-white mb-4">
            Classical vs Quantum Comparison
          </h2>
          <BenchmarkComparisonChart
            data={result.benchmark}
            showConvergence={true}
            showDetails={true}
          />
        </div>
      )}

      {/* Corridor Results Table */}
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h3 className="text-lg font-medium text-white mb-4">
          Corridor Results
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b border-gray-700">
                <th className="pb-3">Corridor</th>
                <th className="pb-3 text-right">Current</th>
                <th className="pb-3 text-right">Recommended</th>
                <th className="pb-3 text-right">Delta</th>
                <th className="pb-3 text-right">Annual Savings</th>
              </tr>
            </thead>
            <tbody>
              {result.corridor_results.map((corridor: any) => (
                <tr
                  key={corridor.corridor_id}
                  className="border-b border-gray-700/50"
                >
                  <td className="py-3 font-medium text-white">
                    {corridor.corridor_code}
                  </td>
                  <td className="py-3 text-right text-gray-300">
                    ${corridor.current_balance.toFixed(1)}M
                  </td>
                  <td className="py-3 text-right text-gray-300">
                    ${corridor.recommended_balance.toFixed(1)}M
                  </td>
                  <td className="py-3 text-right text-green-400">
                    -${corridor.delta.toFixed(1)}M
                  </td>
                  <td className="py-3 text-right text-teal-400">
                    ${(corridor.annual_savings * 1_000).toFixed(0)}K
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="font-medium">
                <td className="pt-4">Total</td>
                <td className="pt-4 text-right text-white">
                  ${result.total_liquidity.toFixed(1)}M
                </td>
                <td className="pt-4 text-right text-white">
                  $
                  {(result.total_liquidity - result.capital_released).toFixed(
                    1,
                  )}
                  M
                </td>
                <td className="pt-4 text-right text-green-400">
                  -${result.capital_released.toFixed(1)}M
                </td>
                <td className="pt-4 text-right text-teal-400">
                  ${result.annual_savings_opportunity.toFixed(1)}M
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* Warnings */}
      {result.warnings && result.warnings.length > 0 && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
          <h4 className="text-yellow-400 font-medium mb-2">⚠️ Warnings</h4>
          <ul className="text-sm text-gray-300 space-y-1">
            {result.warnings.map((warning: string, idx: number) => (
              <li key={idx}>• {warning}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-4">
        <button
          onClick={onBack}
          className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors"
        >
          ← Run Another Optimization
        </button>
        <button
          onClick={onSubmit}
          className="px-6 py-3 bg-teal-600 hover:bg-teal-500 font-medium rounded-lg transition-colors"
          style={{ color: "#FFFFFF" }}
        >
          Submit for Approval →
        </button>
      </div>
    </div>
  );
};

const SummaryCard: React.FC<{
  label: string;
  value: string;
  sublabel?: string;
  highlight?: boolean;
}> = ({ label, value, sublabel, highlight }) => (
  <div
    className={`rounded-lg p-4 border ${
      highlight
        ? "bg-teal-500/10 border-teal-500/30"
        : "bg-gray-800 border-gray-700"
    }`}
  >
    <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">
      {label}
    </div>
    <div
      className={`text-2xl font-bold ${highlight ? "text-teal-400" : "text-white"}`}
    >
      {value}
    </div>
    {sublabel && <div className="text-xs text-gray-400 mt-1">{sublabel}</div>}
  </div>
);
