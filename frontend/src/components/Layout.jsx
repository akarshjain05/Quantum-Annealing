import { NavLink } from "react-router-dom";
import { useEffect, useState } from "react";
import client from "../api/client";

const NAV = [
  { to: "/", label: "Executive Summary", end: true },
  { to: "/corridors", label: "Corridor Management" },
  { to: "/optimizer", label: "Liquidity Optimizer" },
  { to: "/qubo", label: "QUBO Formulation" },
  { type: "divider" },
  { to: "/scenarios", label: "What-If Scenarios" },
  { to: "/stress", label: "Stress Testing" },
  { to: "/agent", label: "Compliance Agent" },
  { type: "divider" },
  { to: "/audit", label: "Compliance & Audit" },
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
        <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto">
          {NAV.map((item, idx) => {
            if (item.type === "divider") {
              return (
                <div
                  key={`div-${idx}`}
                  className="my-3 border-t border-border/50 mx-2"
                />
              );
            }
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium transition-colors ${item.indent ? "ml-4 text-xs" : ""} ${
                    isActive
                      ? "bg-raised text-text border border-border"
                      : "text-muted hover:text-text hover:bg-raised/60"
                  }`
                }
              >
                <span>{item.label}</span>
                {item.hasBadge && pendingCount > 0 && (
                  <span className="bg-teal text-bg text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                    {pendingCount}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
      </aside>
      <main className="flex-1 min-w-0">
        <div className="p-6 max-w-[1400px]">{children}</div>
      </main>
    </div>
  );
}
