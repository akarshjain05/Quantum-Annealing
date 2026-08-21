import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/corridors", label: "Corridors" },
  { to: "/optimizer", label: "Optimizer" },
  { to: "/qubo", label: "QUBO Inspector" },
  { to: "/scenarios", label: "Scenarios" },
  { to: "/stress-tests", label: "Stress Tests" },
  { to: "/agent", label: "Agent" },
  { to: "/audit", label: "Audit Trail" },
];

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

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
