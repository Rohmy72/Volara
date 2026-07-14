import { useState } from "react";

const WINDOWS = [
  { key: "week", label: "Week" },
  { key: "month", label: "Month" },
  { key: "year", label: "Year" },
];

export default function BuzzwordLeaderboard({ buzzwords }) {
  const [window, setWindow] = useState("week");
  const rows = buzzwords[window] || [];
  const maxLift = rows.length ? Math.max(...rows.map((r) => r.lift)) : 1;

  return (
    <div className="panel lb-panel">
      <h3>Trending buzzwords</h3>
      <p className="muted lb-sub">
        Headline terms that lined up with the biggest idiosyncratic moves across
        all tracked stocks in the window.
      </p>

      <div className="chip-row seg">
        {WINDOWS.map((w) => (
          <button
            key={w.key}
            className={`chip ${window === w.key ? "chip-active" : ""}`}
            onClick={() => setWindow(w.key)}
          >
            {w.label}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <p className="muted">
          Not enough news in this window to surface trends (free feeds skew
          recent — try a shorter window).
        </p>
      ) : (
        <ol className="buzz-lb-list">
          {rows.map((r, i) => (
            <li key={r.word} title={r.example_headline}>
              <span className="buzz-rank">{i + 1}</span>
              <div className="buzz-body">
                <div className="buzz-top">
                  <span className="buzzword-pill">{r.word}</span>
                  <span className="buzz-lift">{r.lift}×</span>
                </div>
                <div className="buzz-meta">
                  {r.tickers.join(" · ")} — avg {r.avg_move_pct}% move
                </div>
                <span className="lb-bar-track">
                  <span
                    className="lb-bar lb-bar-buzz"
                    style={{ width: `${Math.max(8, (r.lift / maxLift) * 100)}%` }}
                  />
                </span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
