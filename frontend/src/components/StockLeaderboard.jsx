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
              title={`${r.name} · ${r.sector} · ${r.verdict_label}`}
            >
              <span className="lb-ticker">{r.ticker}</span>
              <span className="lb-bar-track">
                <span
                  className={`lb-bar lb-bar-${tone}`}
                  style={{ width: `${Math.max(8, (r.nrr / maxNrr) * 100)}%` }}
                />
              </span>
              <span className="lb-nrr">{r.nrr.toFixed(2)}</span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
