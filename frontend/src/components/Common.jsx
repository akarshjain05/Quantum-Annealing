export function Kpi({ label, value, sub, tone = "default" }) {
  const toneClass = {
    default: "text-text",
    gold: "text-gold",
    teal: "text-teal",
    red: "text-red",
  }[tone];

  return (
    <div className="card px-4 py-3.5">
      <div className="text-[11px] uppercase tracking-wide text-muted font-mono">{label}</div>
      <div className={`font-display text-2xl font-semibold mt-1 tabular ${toneClass}`}>{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  );
}

const SOURCE_LABELS = {
  REGULATION: "Regulation",
  SETTLEMENT_PRACTICE: "Settlement practice",
  MODEL_ASSUMPTION: "Model assumption",
};

export function SourceTag({ type }) {
  const cls = {
    REGULATION: "tag-regulation",
    SETTLEMENT_PRACTICE: "tag-practice",
    MODEL_ASSUMPTION: "tag-assumption",
  }[type] || "tag-assumption";
  return <span className={`tag ${cls}`}>{SOURCE_LABELS[type] || type}</span>;
}

export function Loading({ label = "Loading" }) {
  return (
    <div className="flex items-center gap-2 text-muted text-sm py-8 justify-center">
      <span className="inline-block w-3 h-3 rounded-full border-2 border-teal border-t-transparent animate-spin" />
      {label}...
    </div>
  );
}

export function EmptyState({ title, hint }) {
  return (
    <div className="card px-6 py-10 text-center">
      <div className="font-display text-text font-medium">{title}</div>
      {hint && <div className="text-sm text-muted mt-1.5">{hint}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="card border-red/40 px-6 py-6 text-center">
      <div className="text-red font-medium text-sm">{message || "Something went wrong."}</div>
      {onRetry && (
        <button onClick={onRetry} className="mt-3 text-xs px-3 py-1.5 rounded-md border border-border text-muted hover:text-text hover:border-teal transition-colors">
          Retry
        </button>
      )}
    </div>
  );
}

export function Skeleton({ className = "" }) {
  return <div className={`animate-pulse bg-raised rounded ${className}`} />;
}
