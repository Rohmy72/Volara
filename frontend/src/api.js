const BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      // ignore JSON parse failure, fall back to statusText
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function analyzeTicker(ticker, period = "1y") {
  return getJSON(
    `${BASE_URL}/api/analyze/${encodeURIComponent(ticker)}?period=${encodeURIComponent(period)}`
  );
}

export async function fetchLeaderboard() {
  return getJSON(`${BASE_URL}/api/leaderboard`);
}
