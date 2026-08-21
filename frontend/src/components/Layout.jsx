import { NavLink } from "react-router-dom";
// import { useAuth } from "../AuthContext";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/corridors", label: "Corridors" },
  { to: "/optimizer", label: "Optimizer" },
  { to: "/approvals", label: "Approvals" },
  { to: "/qubo", label: "QUBO Inspector" },
  { to: "/scenarios", label: "Scenarios" },
  { to: "/stress-tests", label: "Stress Tests" },
  { to: "/agent", label: "Agent" },
  { to: "/audit", label: "Audit Trail" },
];

export default function Layout({ children }) {
  return (
    <div className="min-h-screen flex">
      <aside className="w-60 shrink-0 border-r border-border bg-surface flex flex-col">
        <div className="px-5 py-5 border-b border-border">
          <div className="font-display text-lg font-semibold tracking-tight">
            Nostro<span className="text-teal">Q</span>
          </div>
          <div className="text-[11px] text-muted mt-0.5 leading-tight">
            Quantum-ready liquidity intelligence
          </div>
        </div>
        <nav className="flex-1 py-3 px-2 space-y-0.5">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-raised text-text border border-border"
                    : "text-muted hover:text-text hover:bg-raised/60"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-3 py-4 border-t border-border">
          <div className="px-2 mb-2">
            <div className="text-xs text-text truncate">Demo User</div>
            <div className="text-[11px] text-muted truncate">treasury@demo-bank.com</div>
          </div>
        </div>
      </aside>
      <main className="flex-1 min-w-0">
        <div className="border-b border-border bg-bg/80 backdrop-blur px-6 py-2.5 flex items-center justify-between">
          <span className="text-[11px] text-muted font-mono">
            Decision-support prototype - no live financial transactions are executed.
          </span>
          <span className="text-[11px] text-gold font-mono">
            Synthetic demonstration data
          </span>
        </div>
        <div className="p-6 max-w-[1400px]">{children}</div>
      </main>
    </div>
  );
}
