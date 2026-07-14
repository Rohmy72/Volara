import { useState } from "react";

const PERIODS = [
  { value: "3mo", label: "3 months" },
  { value: "6mo", label: "6 months" },
  { value: "1y", label: "1 year" },
  { value: "2y", label: "2 years" },
];

export default function TickerForm({ onSubmit, loading }) {
  const [ticker, setTicker] = useState("");
  const [period, setPeriod] = useState("1y");

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = ticker.trim().toUpperCase();
    if (!trimmed) return;
    onSubmit(trimmed, period);
  }

  return (
    <form className="ticker-form" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Ticker, e.g. AAPL"
        value={ticker}
        onChange={(e) => setTicker(e.target.value)}
        maxLength={10}
        autoFocus
      />
      <select value={period} onChange={(e) => setPeriod(e.target.value)}>
        {PERIODS.map((p) => (
          <option key={p.value} value={p.value}>
            {p.label}
          </option>
        ))}
      </select>
      <button type="submit" disabled={loading || !ticker.trim()}>
        {loading ? "Analyzing…" : "Analyze"}
      </button>
    </form>
  );
}
