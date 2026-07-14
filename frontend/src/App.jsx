import { useEffect, useState } from "react";
import TopNav from "./components/TopNav.jsx";
import TickerForm from "./components/TickerForm.jsx";
import VerdictCard from "./components/VerdictCard.jsx";
import PriceChart from "./components/PriceChart.jsx";
import BuzzwordList from "./components/BuzzwordList.jsx";
import NewsList from "./components/NewsList.jsx";
import Leaderboards from "./components/Leaderboards.jsx";
import NewsBetaPage from "./components/NewsBetaPage.jsx";
import { analyzeTicker } from "./api.js";

// Tiny hash router — one extra page doesn't warrant a routing library.
function useHashRoute() {
  const [route, setRoute] = useState(window.location.hash);
  useEffect(() => {
    const onChange = () => {
      setRoute(window.location.hash);
      window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export default function App() {
  const route = useHashRoute();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(ticker, period = "1y") {
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeTicker(ticker, period);
      setData(result);
    } catch (err) {
      setError(err.message || "Something went wrong");
      setData(null);
    } finally {
      setLoading(false);
    }
  }

  if (route.startsWith("#/news-beta")) {
    return (
      <div className="app">
        <TopNav />
        <NewsBetaPage />
      </div>
    );
  }

  return (
    <div className="app">
      <TopNav />
      <div className="layout">
        <Leaderboards onSelectTicker={(t) => handleSubmit(t)} />

        <div className="main-col">
          <header className="app-header">
            <h1>Is this stock news-driven?</h1>
            <p className="muted">
              Enter a ticker to see whether its volatility tracks news coverage, and which
              headline terms line up with its biggest moves.
            </p>
            <TickerForm onSubmit={handleSubmit} loading={loading} />
          </header>

          {error && <div className="error-banner">{error}</div>}

          {loading && !data && (
            <div className="loading-state">Analyzing…</div>
          )}

          {!loading && !data && !error && (
            <div className="empty-state">
              <p className="muted">
                Pick a stock from the leaderboards on the left, or search a ticker
                above to run a full analysis.
              </p>
            </div>
          )}

          {data && (
            <main className="results">
              <VerdictCard
                ticker={data.ticker}
                companyName={data.company_name}
                marketBenchmark={data.market_benchmark}
                verdict={data.verdict}
              />
              <PriceChart priceSeries={data.price_series} />
              <div className="results-grid">
                <BuzzwordList buzzwords={data.buzzwords} />
                <NewsList news={data.news} />
              </div>
            </main>
          )}
        </div>
      </div>
    </div>
  );
}
