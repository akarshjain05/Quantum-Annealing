const HOUR_LABELS = [0, 4, 8, 12, 16, 20];

export default function SettlementTimeline({ corridors }) {
  const now = new Date();
  const nowPct = ((now.getUTCHours() * 60 + now.getUTCMinutes()) / (24 * 60)) * 100;

  return (
    <div className="card px-4 py-4">
      <div className="flex items-baseline justify-between mb-1">
        <div className="text-[11px] uppercase tracking-wide text-muted font-mono">
          Settlement windows, 24h UTC
        </div>
        <div className="text-[11px] text-red font-mono flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-red inline-block" />
          now {String(now.getUTCHours()).padStart(2, "0")}:{String(now.getUTCMinutes()).padStart(2, "0")} UTC
        </div>
      </div>

      <div className="pl-16 relative mb-1.5">
        <div className="grid grid-cols-6 text-[10px] text-faint font-mono">
          {HOUR_LABELS.map((h) => (
            <div key={h}>{String(h).padStart(2, "0")}:00</div>
          ))}
        </div>
      </div>

      <div className="space-y-1.5 relative">
        {corridors.map((c) => {
          const [start, end] = c.settlement_window_utc;
          const startPct = (start / 24) * 100;
          const widthPct = ((end - start) / 24) * 100;
          const cutoffPct = (c.cutoff_hour_utc / 24) * 100;
          return (
            <div key={c.code} className="flex items-center gap-2">
              <div className="w-14 shrink-0 text-[11px] font-mono text-muted truncate" title={c.code}>
                {c.code}
              </div>
              <div className="timeline-track flex-1">
                <div className="timeline-hour-grid">
                  {Array.from({ length: 24 }).map((_, i) => <div key={i} />)}
                </div>
                <div
                  className="absolute top-0 bottom-0 bg-teal/20 border-l border-r border-teal/50"
                  style={{ left: `${startPct}%`, width: `${widthPct}%` }}
                  title={`Settlement window ${start}:00-${end}:00 UTC`}
                />
                <div
                  className="absolute top-0 bottom-0 w-[2px] bg-gold"
                  style={{ left: `${cutoffPct}%` }}
                  title={`Cut-off ${c.cutoff_hour_utc}:00 UTC`}
                />
                <div className="timeline-now-marker" style={{ left: `${nowPct}%` }} />
              </div>
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-4 mt-3 text-[10px] text-muted font-mono">
        <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-teal/30 border border-teal/50 inline-block" /> settlement window</span>
        <span className="flex items-center gap-1"><span className="w-0.5 h-2.5 bg-gold inline-block" /> cut-off</span>
        <span className="flex items-center gap-1"><span className="w-0.5 h-2.5 bg-red inline-block" /> now</span>
      </div>
    </div>
  );
}
