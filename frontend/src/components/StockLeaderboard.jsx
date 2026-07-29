import { useMemo, useState } from "react";

const TOP_N = 5;

export default function StockLeaderboard({ stocks, sectors, onSelectTicker }) {
  const [sector, setSector] = useState("All");

  const filtered = useMemo(() => {
    const list = sector === "All" ? stocks : stocks.filter((s) => s.sector === sector);
    // stocks arrive sorted by NRR desc from the API.
    return list;
  }, [stocks, sector]);

  const most = filtered.slice(0, TOP_N);
  const least = filtered.slice(-TOP_N).reverse();
  const topMover = useMemo(() => biggestMover(filtered), [filtered]);

  return (
    <div className="panel lb-panel">
      <h3>News-driven leaderboard</h3>
      <p className="muted lb-sub">
        Ranked by News Beta — how much bigger a stock's idiosyncratic
        moves are on news days vs quiet days.{" "}
        <a className="inline-link" href="#/news-beta">
          What is News Beta?
        </a>
      </p>

      <div className="chip-row">
        <button
          className={`chip ${sector === "All" ? "chip-active" : ""}`}
          onClick={() => setSector("All")}
        >
          All
        </button>
        {sectors.map((s) => (
          <button
            key={s}
            className={`chip ${sector === s ? "chip-active" : ""}`}
            onClick={() => setSector(s)}
          >
            {s}
          </button>
        ))}
      </div>

      {topMover && (
        <p className="lb-mover">
          Biggest mover:{" "}
          <button className="lb-mover-ticker" onClick={() => onSelectTicker(topMover.ticker)}>
            {topMover.ticker}
          </button>{" "}
          <Movement stock={topMover} />
          <span className="muted"> since last update</span>
        </p>
      )}

      {filtered.length === 0 ? (
        <p className="muted">No ranked stocks in this sector.</p>
      ) : (
        <>
          <LbSection
            title="Most news-driven"
            rows={most}
            tone="high"
            onSelectTicker={onSelectTicker}
          />
          {filtered.length > TOP_N && (
            <LbSection
              title="Least news-driven"
              rows={least}
              tone="low"
              onSelectTicker={onSelectTicker}
            />
          )}
        </>
      )}
    </div>
  );
}

// Largest absolute rank change since the previous snapshot (new entries and
// unchanged rows don't count as "movers").
function biggestMover(rows) {
  let best = null;
  for (const r of rows) {
    if (typeof r.rank_delta !== "number" || r.rank_delta === 0) continue;
    if (!best || Math.abs(r.rank_delta) > Math.abs(best.rank_delta)) best = r;
  }
  return best;
}

function LbSection({ title, rows, tone, onSelectTicker }) {
  const maxNrr = Math.max(...rows.map((r) => r.nrr), 1);
  return (
    <div className="lb-section">
      <div className={`lb-section-title lb-${tone}`}>{title}</div>
      <ol className="lb-list">
        {rows.map((r) => (
          <li key={r.ticker}>
            <button
              className="lb-row"
              onClick={() => onSelectTicker(r.ticker)}
              title={rowTitle(r)}
            >
              <span className="lb-ticker">{r.ticker}</span>
              <span className="lb-bar-track">
                <span
                  className={`lb-bar lb-bar-${tone}`}
                  style={{ width: `${Math.max(8, (r.nrr / maxNrr) * 100)}%` }}
                />
              </span>
              <span className="lb-nrr">{r.nrr.toFixed(2)}</span>
              <Movement stock={r} />
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}

function rowTitle(r) {
  let t = `${r.name} · ${r.sector} · ${r.verdict_label}`;
  if (r.is_new) {
    t += " · new to the board";
  } else if (typeof r.nrr_delta === "number" && r.nrr_delta !== 0) {
    const sign = r.nrr_delta > 0 ? "+" : "";
    t += ` · News Beta ${sign}${r.nrr_delta.toFixed(2)} since last update`;
  }
  return t;
}

// Rank-movement badge vs the previous snapshot. Renders nothing for snapshots
// built before movement tracking existed (fields simply absent).
function Movement({ stock }) {
  if (stock.is_new) {
    return <span className="lb-move lb-move-new">NEW</span>;
  }
  if (typeof stock.rank_delta !== "number") {
    return <span className="lb-move lb-move-flat" aria-hidden="true" />;
  }
  if (stock.rank_delta === 0) {
    return (
      <span className="lb-move lb-move-flat" title="No change">
        –
      </span>
    );
  }
  const up = stock.rank_delta > 0;
  return (
    <span
      className={`lb-move ${up ? "lb-move-up" : "lb-move-down"}`}
      title={`${up ? "Up" : "Down"} ${Math.abs(stock.rank_delta)} since last update`}
    >
      {up ? "▲" : "▼"}
      {Math.abs(stock.rank_delta)}
    </span>
  );
}
