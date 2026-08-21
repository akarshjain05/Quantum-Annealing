// frontend/src/components/benchmark/BenchmarkChart.tsx
/**
 * Main Benchmark Comparison Chart Component
 * 
 * Displays Classical vs Quantum solver comparison with:
 * - Execution time bar chart
 * - Solution quality comparison
 * - Detailed results table
 * - Convergence visualization
 */

import React, { useMemo, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  LineChart,
  Line,
  ReferenceLine
} from 'recharts';

// =============================================================================
// TYPES
// =============================================================================

export interface SolverResult {
  solver_type: string;
  solver_category: string;
  display_name: string;
  is_quantum: boolean;
  energy: number;
  execution_time_ms: number;
  solution_quality: number;
  gap_from_best: number;
  gap_percent: number;
  iterations?: number;
  num_reads?: number;
  convergence_data: Array<{ iteration: number; energy: number }>;
  metadata: Record<string, any>;
}

export interface BenchmarkData {
  problem_size: number;
  problem_hash: string;
  best_energy: number;
  best_solver: string | null;
  timestamp: string;
  total_time_ms: number;
  solvers: SolverResult[];
  summary?: {
    num_classical: number;
    num_quantum: number;
    avg_classical_time_ms: number | null;
    avg_quantum_time_ms: number | null;
    best_classical_energy: number | null;
    best_quantum_energy: number | null;
  };
}

interface BenchmarkChartProps {
  data: BenchmarkData;
  showConvergence?: boolean;
  showDetails?: boolean;
  className?: string;
}

// =============================================================================
// CONSTANTS
// =============================================================================

const COLORS = {
  classical: '#14b8a6',      // Teal
  classicalLight: '#5eead4',
  quantum: '#8b5cf6',        // Purple
  quantumLight: '#a78bfa',
  best: '#22c55e',           // Green
  warning: '#f59e0b',        // Amber
  grid: '#374151',
  text: '#9ca3af',
  background: '#1f2937'
};

const SOLVER_DISPLAY_NAMES: Record<string, string> = {
  'classical_sa_numpy': 'Classical SA',
  'classical_simulated_annealing': 'Classical SA',
  'dwave_neal_sa': 'D-Wave Neal SA',
  'dwave_simulated_annealing': 'D-Wave SA',
  'dwave_exact': 'Exact Solver',
  'qaoa_custom': 'QAOA',
  'qiskit_qaoa': 'Qiskit QAOA',
  'qiskit_qaoa_simulator': 'QAOA Simulator'
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

const formatTime = (ms: number): string => {
  if (ms < 1) return `${(ms * 1000).toFixed(0)}μs`;
  if (ms < 1000) return `${ms.toFixed(1)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
};

const formatEnergy = (energy: number): string => {
  return energy.toFixed(2);
};

const getSolverColor = (isQuantum: boolean, isBest: boolean = false): string => {
  if (isBest) return COLORS.best;
  return isQuantum ? COLORS.quantum : COLORS.classical;
};

const getDisplayName = (solverType: string, displayName?: string): string => {
  return displayName || SOLVER_DISPLAY_NAMES[solverType] || solverType;
};

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

/**
 * Summary Statistics Header
 */
const BenchmarkSummary: React.FC<{ data: BenchmarkData }> = ({ data }) => {
  const classicalSolvers = data.solvers.filter(s => !s.is_quantum);
  const quantumSolvers = data.solvers.filter(s => s.is_quantum);

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">
          Problem Size
        </div>
        <div className="text-2xl font-bold text-white">
          {data.problem_size}
        </div>
        <div className="text-xs text-gray-400">variables</div>
      </div>
      
      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">
          Best Energy
        </div>
        <div className="text-2xl font-bold text-green-400">
          {formatEnergy(data.best_energy)}
        </div>
        <div className="text-xs text-gray-400">
          by {getDisplayName(data.best_solver || '')}
        </div>
      </div>
      
      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">
          Solvers Tested
        </div>
        <div className="text-2xl font-bold text-white">
          {data.solvers.length}
        </div>
        <div className="text-xs text-gray-400">
          <span className="text-teal-400">{classicalSolvers.length} classical</span>
          {quantumSolvers.length > 0 && (
            <>, <span className="text-purple-400">{quantumSolvers.length} quantum</span></>
          )}
        </div>
      </div>
      
      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">
          Total Time
        </div>
        <div className="text-2xl font-bold text-white">
          {formatTime(data.total_time_ms)}
        </div>
        <div className="text-xs text-gray-400">all solvers</div>
      </div>
    </div>
  );
};

/**
 * Execution Time Bar Chart
 */
const ExecutionTimeChart: React.FC<{ solvers: SolverResult[]; bestSolver: string | null }> = ({ 
  solvers, 
  bestSolver 
}) => {
  const chartData = useMemo(() => {
    return solvers.map(s => ({
      name: getDisplayName(s.solver_type, s.display_name),
      time: s.execution_time_ms,
      isQuantum: s.is_quantum,
      isBest: s.solver_type === bestSolver,
      fullName: s.display_name
    })).sort((a, b) => a.time - b.time);
  }, [solvers, bestSolver]);

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const data = payload[0].payload;
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 shadow-lg">
        <p className="font-medium text-white">{data.fullName}</p>
        <p className="text-sm text-gray-400">
          Time: <span className="text-teal-400 font-medium">{formatTime(data.time)}</span>
        </p>
        <p className="text-xs text-gray-500 mt-1">
          {data.isQuantum ? '🔮 Quantum' : '💻 Classical'}
        </p>
      </div>
    );
  };

  return (
    <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
      <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
        Execution Time Comparison
      </h4>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} horizontal={true} vertical={false} />
            <XAxis 
              type="number" 
              stroke={COLORS.text}
              tickFormatter={(v) => formatTime(v)}
              fontSize={12}
            />
            <YAxis 
              dataKey="name" 
              type="category" 
              stroke={COLORS.text}
              width={120}
              fontSize={12}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="time" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={getSolverColor(entry.isQuantum, entry.isBest)}
                  opacity={entry.isBest ? 1 : 0.8}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-gray-500 mt-3">
        Lower is better. Quantum simulators have overhead; real QPU timing would differ.
      </p>
    </div>
  );
};

/**
 * Solution Quality Chart
 */
const SolutionQualityChart: React.FC<{ solvers: SolverResult[]; bestSolver: string | null }> = ({ 
  solvers,
  bestSolver 
}) => {
  const chartData = useMemo(() => {
    return solvers.map(s => ({
      name: getDisplayName(s.solver_type, s.display_name),
      quality: s.solution_quality,
      energy: s.energy,
      isQuantum: s.is_quantum,
      isBest: s.solver_type === bestSolver,
      gap: s.gap_percent
    })).sort((a, b) => b.quality - a.quality);
  }, [solvers, bestSolver]);

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload?.length) return null;
    const data = payload[0].payload;
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 shadow-lg">
        <p className="font-medium text-white">{data.name}</p>
        <p className="text-sm text-gray-400">
          Quality: <span className="text-green-400 font-medium">{data.quality.toFixed(2)}%</span>
        </p>
        <p className="text-sm text-gray-400">
          Energy: <span className="text-white">{formatEnergy(data.energy)}</span>
        </p>
        {data.gap > 0 && (
          <p className="text-xs text-yellow-400 mt-1">
            Gap from optimal: {data.gap.toFixed(2)}%
          </p>
        )}
      </div>
    );
  };

  const minQuality = Math.min(...chartData.map(d => d.quality));
  const domainMin = Math.max(0, Math.floor(minQuality - 5));

  return (
    <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
      <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
        Solution Quality (% of Optimal)
      </h4>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ left: 20, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} horizontal={true} vertical={false} />
            <XAxis 
              type="number" 
              domain={[domainMin, 100]}
              stroke={COLORS.text}
              tickFormatter={(v) => `${v}%`}
              fontSize={12}
            />
            <YAxis 
              dataKey="name" 
              type="category" 
              stroke={COLORS.text}
              width={120}
              fontSize={12}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine x={100} stroke={COLORS.best} strokeDasharray="5 5" />
            <Bar dataKey="quality" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.quality >= 99.9 ? COLORS.best : getSolverColor(entry.isQuantum)}
                  opacity={entry.isBest ? 1 : 0.8}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-gray-500 mt-3">
        100% = optimal solution found. Green line indicates optimum.
      </p>
    </div>
  );
};

/**
 * Convergence Chart
 */
const ConvergenceChart: React.FC<{ solvers: SolverResult[] }> = ({ solvers }) => {
  const solversWithConvergence = solvers.filter(
    s => s.convergence_data && s.convergence_data.length > 1
  );

  if (solversWithConvergence.length === 0) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
          Convergence History
        </h4>
        <div className="h-64 flex items-center justify-center text-gray-500">
          No convergence data available
        </div>
      </div>
    );
  }

  const chartData = useMemo(() => {
    const maxIterations = Math.max(
      ...solversWithConvergence.map(s => s.convergence_data.length)
    );
    
    const data: Array<Record<string, any>> = [];
    
    for (let i = 0; i < maxIterations; i++) {
      const point: Record<string, any> = { iteration: i };
      
      for (const solver of solversWithConvergence) {
        const key = getDisplayName(solver.solver_type, solver.display_name);
        if (i < solver.convergence_data.length) {
          point[key] = solver.convergence_data[i].energy;
        }
      }
      
      data.push(point);
    }
    
    return data;
  }, [solversWithConvergence]);

  const lineColors = [COLORS.classical, COLORS.quantum, COLORS.best, COLORS.warning];

  return (
    <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
      <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
        Convergence History
      </h4>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ left: 20, right: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
            <XAxis 
              dataKey="iteration" 
              stroke={COLORS.text}
              fontSize={12}
              label={{ value: 'Iteration', position: 'bottom', fill: COLORS.text }}
            />
            <YAxis 
              stroke={COLORS.text}
              fontSize={12}
              label={{ value: 'Energy', angle: -90, position: 'insideLeft', fill: COLORS.text }}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: COLORS.background, 
                border: `1px solid ${COLORS.grid}`,
                borderRadius: '8px'
              }}
            />
            <Legend />
            {solversWithConvergence.map((solver, idx) => (
              <Line
                key={solver.solver_type}
                type="monotone"
                dataKey={getDisplayName(solver.solver_type, solver.display_name)}
                stroke={solver.is_quantum ? COLORS.quantum : lineColors[idx % lineColors.length]}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-gray-500 mt-3">
        Energy should decrease (improve) over iterations for optimization algorithms.
      </p>
    </div>
  );
};

/**
 * Detailed Results Table
 */
const ResultsTable: React.FC<{ solvers: SolverResult[]; bestSolver: string | null }> = ({ 
  solvers,
  bestSolver 
}) => {
  const sortedSolvers = useMemo(() => {
    return [...solvers].sort((a, b) => a.energy - b.energy);
  }, [solvers]);

  return (
    <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
      <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
        Detailed Results
      </h4>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-500 border-b border-gray-700">
              <th className="pb-3 pr-4">Solver</th>
              <th className="pb-3 pr-4">Type</th>
              <th className="pb-3 pr-4 text-right">Energy</th>
              <th className="pb-3 pr-4 text-right">Time</th>
              <th className="pb-3 pr-4 text-right">Quality</th>
              <th className="pb-3 text-right">Gap</th>
            </tr>
          </thead>
          <tbody>
            {sortedSolvers.map((solver) => {
              const isBest = solver.solver_type === bestSolver;
              return (
                <tr 
                  key={solver.solver_type}
                  className={`border-b border-gray-700/50 ${isBest ? 'bg-green-500/10' : ''}`}
                >
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      {isBest && <span className="text-green-400">🏆</span>}
                      <span className={`font-medium ${isBest ? 'text-green-400' : 'text-white'}`}>
                        {getDisplayName(solver.solver_type, solver.display_name)}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 pr-4">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      solver.is_quantum 
                        ? 'bg-purple-500/20 text-purple-400' 
                        : 'bg-teal-500/20 text-teal-400'
                    }`}>
                      {solver.is_quantum ? '🔮 Quantum' : '💻 Classical'}
                    </span>
                  </td>
                  <td className="py-3 pr-4 text-right font-mono text-gray-300">
                    {formatEnergy(solver.energy)}
                  </td>
                  <td className="py-3 pr-4 text-right text-gray-300">
                    {formatTime(solver.execution_time_ms)}
                  </td>
                  <td className="py-3 pr-4 text-right">
                    <span className={solver.solution_quality >= 99.9 ? 'text-green-400' : 'text-yellow-400'}>
                      {solver.solution_quality.toFixed(2)}%
                    </span>
                  </td>
                  <td className="py-3 text-right text-gray-400">
                    {solver.gap_percent === 0 ? (
                      <span className="text-green-400">Optimal</span>
                    ) : (
                      `+${solver.gap_percent.toFixed(2)}%`
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

/**
 * Quantum vs Classical Summary Card
 */
const QuantumVsClassicalCard: React.FC<{ data: BenchmarkData }> = ({ data }) => {
  const classical = data.solvers.filter(s => !s.is_quantum);
  const quantum = data.solvers.filter(s => s.is_quantum);
  
  if (quantum.length === 0) {
    return (
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
        <h4 className="text-lg font-medium text-blue-400 mb-3">
          ℹ️ Quantum Solvers Not Included
        </h4>
        <p className="text-sm text-gray-300">
          Only classical solvers were run in this benchmark. This could be because:
        </p>
        <ul className="text-sm text-gray-400 list-disc list-inside mt-2 space-y-1">
          <li>Problem size ({data.problem_size} variables) exceeds quantum simulator limits</li>
          <li>Quantum libraries (Qiskit) not installed</li>
          <li>Quantum solvers were disabled in configuration</li>
        </ul>
        <p className="text-sm text-gray-300 mt-4">
          For problems with 20 or fewer variables, QAOA simulation is available.
        </p>
      </div>
    );
  }
  
  const bestClassical = classical.length > 0 
    ? classical.reduce((a, b) => a.energy < b.energy ? a : b)
    : null;
  const bestQuantum = quantum.reduce((a, b) => a.energy < b.energy ? a : b);
  
  const classicalWins = bestClassical && bestClassical.energy <= bestQuantum.energy;
  const quantumWins = !classicalWins;
  
  const timeDiff = bestClassical 
    ? (bestQuantum.execution_time_ms / bestClassical.execution_time_ms)
    : 0;

  return (
    <div className="bg-gradient-to-r from-teal-500/10 to-purple-500/10 border border-gray-700 rounded-lg p-6">
      <h4 className="text-lg font-medium text-white mb-4">
        ⚔️ Classical vs Quantum Comparison
      </h4>
      
      <div className="grid grid-cols-2 gap-6">
        <div className={`p-4 rounded-lg ${classicalWins ? 'bg-teal-500/20 border border-teal-500/30' : 'bg-gray-800/50'}`}>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-2xl">💻</span>
            <span className="font-medium text-white">Classical</span>
            {classicalWins && <span className="text-green-400 text-sm">👑 Winner</span>}
          </div>
          {bestClassical && (
            <>
              <div className="text-sm text-gray-400">
                Best: <span className="text-teal-400">{getDisplayName(bestClassical.solver_type, bestClassical.display_name)}</span>
              </div>
              <div className="text-sm text-gray-400">
                Energy: <span className="text-white font-mono">{formatEnergy(bestClassical.energy)}</span>
              </div>
              <div className="text-sm text-gray-400">
                Time: <span className="text-white">{formatTime(bestClassical.execution_time_ms)}</span>
              </div>
            </>
          )}
        </div>
        
        <div className={`p-4 rounded-lg ${quantumWins ? 'bg-purple-500/20 border border-purple-500/30' : 'bg-gray-800/50'}`}>
          <div className="flex items-center gap-2 mb-3">
            <span className="text-2xl">🔮</span>
            <span className="font-medium text-white">Quantum</span>
            {quantumWins && <span className="text-green-400 text-sm">👑 Winner</span>}
          </div>
          <div className="text-sm text-gray-400">
            Best: <span className="text-purple-400">{getDisplayName(bestQuantum.solver_type, bestQuantum.display_name)}</span>
          </div>
          <div className="text-sm text-gray-400">
            Energy: <span className="text-white font-mono">{formatEnergy(bestQuantum.energy)}</span>
          </div>
          <div className="text-sm text-gray-400">
            Time: <span className="text-white">{formatTime(bestQuantum.execution_time_ms)}</span>
          </div>
        </div>
      </div>
      
      <div className="mt-4 pt-4 border-t border-gray-700">
        <h5 className="text-sm font-medium text-gray-400 mb-2">Analysis</h5>
        <ul className="text-sm text-gray-300 space-y-1">
          <li>
            • Solution quality: {bestClassical && Math.abs(bestClassical.energy - bestQuantum.energy) < 0.01 
              ? 'Both methods found equivalent solutions' 
              : `${classicalWins ? 'Classical' : 'Quantum'} found better solution by ${Math.abs(
                  (bestClassical?.energy || 0) - bestQuantum.energy
                ).toFixed(2)}`
            }
          </li>
          <li>
            • Execution time: Quantum is {timeDiff > 1 
              ? `${timeDiff.toFixed(1)}x slower` 
              : `${(1/timeDiff).toFixed(1)}x faster`
            } than classical
          </li>
          <li className="text-yellow-400">
            • Note: Quantum running on simulator; real QPU performance would differ
          </li>
        </ul>
      </div>
    </div>
  );
};

/**
 * Quantum Advantage Disclosure
 */
const QuantumAdvantageDisclosure: React.FC<{ problemSize: number }> = ({ problemSize }) => {
  return (
    <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-6">
      <h4 className="text-lg font-medium text-yellow-400 mb-3">
        ⚠️ About Quantum Advantage
      </h4>
      <div className="text-sm text-gray-300 space-y-3">
        <p>
          <strong>Current Status:</strong> For this problem size ({problemSize} variables), 
          classical simulated annealing and quantum approaches achieve similar solution quality.
          This is expected and honest.
        </p>
        <p>
          <strong>Where Quantum May Help:</strong>
        </p>
        <ul className="list-disc list-inside text-gray-400 space-y-1 ml-2">
          <li>Problems with 500+ variables (50+ corridors)</li>
          <li>Problems with dense connectivity (many interactions)</li>
          <li>When running on actual quantum hardware (D-Wave, IBM)</li>
          <li>Multi-institution network optimization (future)</li>
        </ul>
        <p>
          <strong>Why Show This:</strong> The QUBO formulation is <em>quantum-ready</em> — 
          the same mathematical model can run on quantum hardware without modification when 
          the problem scale and hardware maturity align.
        </p>
      </div>
    </div>
  );
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export const BenchmarkComparisonChart: React.FC<BenchmarkChartProps> = ({
  data,
  showConvergence = true,
  showDetails = true,
  className = ''
}) => {
  const [activeTab, setActiveTab] = useState<'charts' | 'table' | 'analysis'>('charts');

  if (!data || !data.solvers || data.solvers.length === 0) {
    return (
      <div className={`bg-gray-800 rounded-lg p-8 text-center ${className}`}>
        <p className="text-gray-400">No benchmark data available</p>
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      <BenchmarkSummary data={data} />
      
      <div className="flex items-center gap-6 px-2">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: COLORS.classical }}></div>
          <span className="text-sm text-gray-400">Classical Solvers</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: COLORS.quantum }}></div>
          <span className="text-sm text-gray-400">Quantum Solvers</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: COLORS.best }}></div>
          <span className="text-sm text-gray-400">Best Result</span>
        </div>
      </div>
      
      <div className="flex gap-2 border-b border-gray-700">
        <button
          onClick={() => setActiveTab('charts')}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'charts'
              ? 'text-teal-400 border-b-2 border-teal-400'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Charts
        </button>
        <button
          onClick={() => setActiveTab('table')}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'table'
              ? 'text-teal-400 border-b-2 border-teal-400'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Detailed Table
        </button>
        <button
          onClick={() => setActiveTab('analysis')}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === 'analysis'
              ? 'text-teal-400 border-b-2 border-teal-400'
              : 'text-gray-400 hover:text-white'
          }`}
        >
          Analysis
        </button>
      </div>
      
      {activeTab === 'charts' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ExecutionTimeChart solvers={data.solvers} bestSolver={data.best_solver} />
            <SolutionQualityChart solvers={data.solvers} bestSolver={data.best_solver} />
          </div>
          
          {showConvergence && <ConvergenceChart solvers={data.solvers} />}
        </div>
      )}
      
      {activeTab === 'table' && (
        <ResultsTable solvers={data.solvers} bestSolver={data.best_solver} />
      )}
      
      {activeTab === 'analysis' && (
        <div className="space-y-6">
          <QuantumVsClassicalCard data={data} />
          <QuantumAdvantageDisclosure problemSize={data.problem_size} />
        </div>
      )}
    </div>
  );
};

export default BenchmarkComparisonChart;
