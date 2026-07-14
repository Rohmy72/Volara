export default function BuzzwordList({ buzzwords }) {
  if (!buzzwords.length) {
    return (
      <div className="panel">
        <h3>Volatility buzzwords</h3>
        <p className="muted">
          Not enough repeated terms across news days to surface a reliable pattern yet.
        </p>
      </div>
    );
  }

  const maxLift = Math.max(...buzzwords.map((b) => b.lift));

  return (
    <div className="panel">
      <h3>Volatility buzzwords</h3>
      <p className="muted">
        Terms that tend to appear in headlines on this stock's bigger idiosyncratic-move
        days, versus its average news day. Correlational, not causal.
      </p>
      <ul className="buzzword-list">
        {buzzwords.map((b) => (
          <li key={b.word} title={b.example_headline}>
            <span
              className="buzzword-pill"
              style={{ fontSize: `${0.85 + (b.lift / maxLift) * 0.65}rem` }}
            >
              {b.word}
            </span>
            <span className="buzzword-meta">
              {b.lift}x · {b.occurrences} day{b.occurrences === 1 ? "" : "s"} · avg{" "}
              {b.avg_move_pct}% move
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
