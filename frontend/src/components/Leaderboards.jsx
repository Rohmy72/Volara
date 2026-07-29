import { useEffect, useState } from "react";
import StockLeaderboard from "./StockLeaderboard.jsx";
import BuzzwordLeaderboard from "./BuzzwordLeaderboard.jsx";
import { fetchLeaderboard } from "../api.js";

// Human-readable freshness from the snapshot's age (falls back to the raw date
// for snapshots served without an age_hours field).
function freshnessLabel(data) {
  const age = data.age_hours;
  if (typeof age !== "number") {
    return `Updated ${new Date(data.generated_at).toLocaleDateString()}`;
  }
  if (age < 1) return "Updated just now";
  if (age < 2) return "Updated 1h ago";
  if (age < 24) return `Updated ${Math.round(age)}h ago`;
  const days = Math.round(age / 24);
  return `Updated ${days}d ago`;
}

export default function Leaderboards({ onSelectTicker }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let alive = true;
    fetchLeaderboard()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e.message || "Failed to load leaderboards"));
    return () => {
      alive = false;
    };
  }, []);

  if (error) {
    return (
      <aside className="sidebar">
        <div className="panel">
          <h3>Leaderboards</h3>
          <p className="muted">{error}</p>
        </div>
      </aside>
    );
  }

  if (!data) {
    return (
      <aside className="sidebar">
        <div className="panel lb-skeleton">
          <h3>Leaderboards</h3>
          <p className="muted">Loading…</p>
        </div>
      </aside>
    );
  }

  return (
    <aside className="sidebar">
      <StockLeaderboard
        stocks={data.stocks}
        sectors={data.sectors}
        onSelectTicker={onSelectTicker}
      />
      <BuzzwordLeaderboard buzzwords={data.buzzwords} />
      <p className="lb-timestamp muted">
        {freshnessLabel(data)} · {data.n_ranked} stocks
        {data.refreshing && <span className="lb-refreshing"> · refreshing…</span>}
      </p>
    </aside>
  );
}
