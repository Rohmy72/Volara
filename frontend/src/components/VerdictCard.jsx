const LABEL_CLASS = {
  "News-driven": "verdict-high",
  "Somewhat news-sensitive": "verdict-mid",
  "Not particularly news-driven": "verdict-low",
  "Not enough data": "verdict-unknown",
};

const DIRECTION_CLASS = {
  "Upside-skewed": "dir-up",
  "Downside-skewed": "dir-down",
  "Two-sided": "dir-mixed",
};

export default function VerdictCard({ ticker, companyName, marketBenchmark, verdict }) {
  const cls = LABEL_CLASS[verdict.label] || "verdict-unknown";
  return (
    <div className={`verdict-card ${cls}`}>
      <div className="verdict-header">
        <h2>
          {companyName} ({ticker})
        </h2>
        <div className="verdict-badges">
          <span className="verdict-badge">{verdict.label}</span>
          {verdict.direction_label && (
            <span
              className={`direction-badge ${DIRECTION_CLASS[verdict.direction_label] || ""}`}
            >
              {verdict.direction_label}
            </span>
          )}
        </div>
      </div>
      <p className="verdict-explanation">{verdict.explanation}</p>

      <DirectionSplit verdict={verdict} />

      <div className="verdict-stats">
        <Stat
          label="News Beta"
          value={verdict.news_reaction_ratio ?? "—"}
          hint="Idiosyncratic move size on news days vs quiet days, after removing the market's effect (vs SPY). See: What is News Beta?"
        />
        <Stat label="News days" value={verdict.n_news_days} />
        <Stat label="Quiet days" value={verdict.n_quiet_days} />
        <Stat
          label="Top-10 moves explained"
          value={
            verdict.top_moves_explained_pct != null
              ? `${verdict.top_moves_explained_pct}%`
              : "—"
          }
          hint="Share of the 10 biggest abnormal-move days that had aligned news coverage"
        />
      </div>
      <p className="verdict-footnote">
        Benchmark used to strip out market-wide moves: {marketBenchmark}. This is a
        correlational signal, not investment advice.
      </p>
    </div>
  );
}

// Which way news-day moves lean. News Beta measures how *big* news-day moves
// are; this shows whether they were gains or losses.
function DirectionSplit({ verdict }) {
  const up = verdict.n_news_up_days;
  const down = verdict.n_news_down_days;
  const total = up + down;
  if (!verdict.direction_label || total === 0) return null;

  const upPct = (up / total) * 100;

  return (
    <div className="direction-block">
      <div className="direction-scale-head">
        <span className="dir-label dir-up-text">
          {up} up {verdict.avg_up_move_pct != null && (
            <span className="dir-avg">avg +{verdict.avg_up_move_pct.toFixed(2)}%</span>
          )}
        </span>
        <span className="dir-label dir-down-text">
          {verdict.avg_down_move_pct != null && (
            <span className="dir-avg">avg {verdict.avg_down_move_pct.toFixed(2)}%</span>
          )}{" "}
          {down} down
        </span>
      </div>
      <div
        className="direction-bar"
        role="img"
        aria-label={`${up} up days, ${down} down days on news`}
      >
        <span className="direction-bar-up" style={{ width: `${upPct}%` }} />
        <span className="direction-bar-down" style={{ width: `${100 - upPct}%` }} />
      </div>
      <p className="direction-explanation">{verdict.direction_explanation}</p>
    </div>
  );
}

function Stat({ label, value, hint }) {
  return (
    <div className="stat" title={hint}>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}
