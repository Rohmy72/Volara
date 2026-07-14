import { useEffect, useState } from "react";
import StockLeaderboard from "./StockLeaderboard.jsx";
import BuzzwordLeaderboard from "./BuzzwordLeaderboard.jsx";
import { fetchLeaderboard } from "../api.js";

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
        Snapshot: {new Date(data.generated_at).toLocaleDateString()} · {data.n_ranked}{" "}
        stocks
      </p>
    </aside>
  );
}
