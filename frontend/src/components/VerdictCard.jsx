const LABEL_CLASS = {
  "News-driven": "verdict-high",
  "Somewhat news-sensitive": "verdict-mid",
  "Not particularly news-driven": "verdict-low",
  "Not enough data": "verdict-unknown",
};

export default function VerdictCard({ ticker, companyName, marketBenchmark, verdict }) {
  const cls = LABEL_CLASS[verdict.label] || "verdict-unknown";
  return (
    <div className={`verdict-card ${cls}`}>
      <div className="verdict-header">
        <h2>
          {companyName} ({ticker})
        </h2>
        <span className="verdict-badge">{verdict.label}</span>
      </div>
      <p className="verdict-explanation">{verdict.explanation}</p>
      <div className="verdict-stats">
        <Stat
          label="News Reaction Ratio"
          value={verdict.news_reaction_ratio ?? "—"}
          hint="Idiosyncratic move size on news days vs quiet days, after removing the market's effect (vs SPY)"
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

function Stat({ label, value, hint }) {
  return (
    <div className="stat" title={hint}>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}
