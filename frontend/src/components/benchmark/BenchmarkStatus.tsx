// frontend/src/components/benchmark/BenchmarkStatus.tsx
/**
 * Quantum Solver Status Component
 * 
 * Shows which quantum libraries and solvers are available.
 */

import React from 'react';

interface SolverInfo {
  type: string;
  display_name: string;
  category: string;
  is_available: boolean;
  max_variables?: number;
}

interface QuantumStatus {
  qiskit_available: boolean;
  qiskit_version?: string;
  dwave_available: boolean;
  neal_available: boolean;
  quantum_ready: boolean;
  available_solvers: SolverInfo[];
  message: string;
}

interface BenchmarkStatusProps {
  status: QuantumStatus | null;
  loading?: boolean;
  error?: string;
}

export const BenchmarkStatus: React.FC<BenchmarkStatusProps> = ({
  status,
  loading = false,
  error
}) => {
  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 animate-pulse">
        <div className="h-6 bg-gray-700 rounded w-1/3 mb-4"></div>
        <div className="space-y-3">
          <div className="h-4 bg-gray-700 rounded w-1/2"></div>
          <div className="h-4 bg-gray-700 rounded w-2/3"></div>
          <div className="h-4 bg-gray-700 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6">
        <h3 className="text-lg font-medium text-red-400 mb-2">
          ❌ Error Loading Solver Status
        </h3>
        <p className="text-sm text-gray-400">{error}</p>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <p className="text-gray-400">No status data available</p>
      </div>
    );
  }

  const classicalSolvers = status.available_solvers.filter(
    s => s.category === 'classical' || s.category === 'quantum_inspired'
  );
  const quantumSolvers = status.available_solvers.filter(
    s => s.category === 'quantum_simulation' || s.category === 'quantum_hardware'
  );

  return (
    <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-medium text-white">Quantum Solver Status</h3>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
          status.quantum_ready 
            ? 'bg-green-500/20 text-green-400' 
            : 'bg-yellow-500/20 text-yellow-400'
        }`}>
          {status.quantum_ready ? '✓ Quantum Ready' : '⚠ Classical Only'}
        </span>
      </div>

      {/* Library Status */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <LibraryCard 
          name="Qiskit"
          available={status.qiskit_available}
          version={status.qiskit_version}
          description="Gate-based quantum computing"
        />
        <LibraryCard 
          name="D-Wave dimod"
          available={status.dwave_available}
          description="Quantum annealing framework"
        />
        <LibraryCard 
          name="Neal SA"
          available={status.neal_available}
          description="Production SA solver"
        />
        <LibraryCard 
          name="Quantum Ready"
          available={status.quantum_ready}
          description="QAOA/QA simulation"
          highlight
        />
      </div>

      {/* Solver List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Classical Solvers */}
        <div>
          <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
            💻 Classical Solvers ({classicalSolvers.filter(s => s.is_available).length}/{classicalSolvers.length})
          </h4>
          <div className="space-y-2">
            {classicalSolvers.map(solver => (
              <SolverCard key={solver.type} solver={solver} />
            ))}
          </div>
        </div>

        {/* Quantum Solvers */}
        <div>
          <h4 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
            🔮 Quantum Solvers ({quantumSolvers.filter(s => s.is_available).length}/{quantumSolvers.length})
          </h4>
          <div className="space-y-2">
            {quantumSolvers.length > 0 ? (
              quantumSolvers.map(solver => (
                <SolverCard key={solver.type} solver={solver} />
              ))
            ) : (
              <p className="text-sm text-gray-500 italic">
                No quantum solvers registered
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Message */}
      <div className="mt-6 pt-4 border-t border-gray-700">
        <p className="text-sm text-gray-400">{status.message}</p>
      </div>
    </div>
  );
};

const LibraryCard: React.FC<{
  name: string;
  available: boolean;
  version?: string;
  description: string;
  highlight?: boolean;
}> = ({ name, available, version, description, highlight }) => (
  <div className={`p-3 rounded-lg border ${
    highlight
      ? available 
        ? 'bg-green-500/10 border-green-500/30' 
        : 'bg-yellow-500/10 border-yellow-500/30'
      : 'bg-gray-800/50 border-gray-700'
  }`}>
    <div className="flex items-center gap-2 mb-1">
      <span className={available ? 'text-green-400' : 'text-red-400'}>
        {available ? '✓' : '✗'}
      </span>
      <span className="font-medium text-white text-sm">{name}</span>
    </div>
    {version && (
      <div className="text-xs text-gray-400">v{version}</div>
    )}
    <div className="text-xs text-gray-500 mt-1">{description}</div>
  </div>
);

const SolverCard: React.FC<{ solver: SolverInfo }> = ({ solver }) => (
  <div className={`flex items-center justify-between p-2 rounded ${
    solver.is_available ? 'bg-gray-700/30' : 'bg-gray-800/30 opacity-50'
  }`}>
    <div className="flex items-center gap-2">
      <span className={solver.is_available ? 'text-green-400' : 'text-gray-500'}>
        {solver.is_available ? '●' : '○'}
      </span>
      <span className="text-sm text-gray-300">{solver.display_name}</span>
    </div>
    {solver.max_variables && (
      <span className="text-xs text-gray-500">
        max {solver.max_variables} vars
      </span>
    )}
  </div>
);

export default BenchmarkStatus;
