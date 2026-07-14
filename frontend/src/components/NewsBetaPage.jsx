export default function NewsBetaPage() {
  return (
    <div className="doc-page">
      <a className="inline-link doc-back" href="#/">
        ← Back to analysis
      </a>

      <h1 className="doc-title">What is News Beta?</h1>
      <p className="doc-lede">
        News Beta measures how much of a stock's <em>own</em> volatility clusters
        around news coverage. A stock with a News Beta near 1 moves the same
        whether or not it's in the headlines; a stock with a News Beta of 2+ does
        its big moves almost exclusively on news days.
      </p>

      <div className="doc-formula-hero mono">
        News&nbsp;Beta&nbsp;=&nbsp;
        <span className="frac">
          <span>avg&nbsp;|abnormal&nbsp;move|&nbsp;on&nbsp;news&nbsp;days</span>
          <span>avg&nbsp;|abnormal&nbsp;move|&nbsp;on&nbsp;quiet&nbsp;days</span>
        </span>
      </div>

      <section className="panel doc-section">
        <h3>
          <span className="doc-step mono">1</span> Strip out the market
        </h3>
        <p>
          A stock dropping because the <em>whole market</em> dropped is not news
          reactivity — it's just beta to the index. So the first step removes the
          market's influence. We fit a standard market model against a benchmark
          (SPY by default) over the analysis window:
        </p>
        <pre className="doc-formula mono">
          r<sub>stock</sub> = α + β · r<sub>market</sub> + ε
        </pre>
        <p>
          α and β come from an ordinary least-squares fit of the stock's daily
          returns on the market's daily returns. What's left over each day —
          ε, the <strong>abnormal return</strong> — is the part of the move the
          market can't explain. That residual is the only thing News Beta looks
          at. This is the same market-model approach used in academic event
          studies.
        </p>
      </section>

      <section className="panel doc-section">
        <h3>
          <span className="doc-step mono">2</span> Find the news days
        </h3>
        <p>
          We aggregate headlines for the ticker from several sources (Yahoo
          Finance's feed, Google News RSS, Yahoo Finance RSS, plus Alpha Vantage
          when a key is configured), de-duplicate them by title, and align each
          article to its nearest trading day within a ±1-day window — so a
          Saturday story counts toward Monday's session, and an after-hours story
          counts toward the next open. Every trading day in the window is then
          either a <strong>news day</strong> (≥1 aligned article) or a{" "}
          <strong>quiet day</strong> (none).
        </p>
      </section>

      <section className="panel doc-section">
        <h3>
          <span className="doc-step mono">3</span> Compare the two groups
        </h3>
        <p>
          News Beta is the ratio of the average <em>size</em> of abnormal moves
          (absolute value — direction doesn't matter) on news days versus quiet
          days:
        </p>
        <pre className="doc-formula mono">
          News Beta = mean(|ε| on news days) ÷ mean(|ε| on quiet days)
        </pre>
        <p>
          If news genuinely drives the stock, its market-adjusted moves should be
          systematically bigger when coverage lands. If the stock moves the same
          amount regardless, headlines are mostly narrating moves rather than
          causing them.
        </p>
      </section>

      <section className="panel doc-section">
        <h3>How to read the number</h3>
        <table className="doc-table">
          <thead>
            <tr>
              <th className="mono">News Beta</th>
              <th>Verdict</th>
              <th>Meaning</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="mono">&lt; 1.2</td>
              <td>
                <span className="doc-pill pill-low">Not particularly news-driven</span>
              </td>
              <td>
                News days look like any other day. Volatility comes from flows,
                sector moves, or sentiment — not headlines.
              </td>
            </tr>
            <tr>
              <td className="mono">1.2 – 2.0</td>
              <td>
                <span className="doc-pill pill-mid">Somewhat news-sensitive</span>
              </td>
              <td>
                News is a contributing factor but not the dominant driver of the
                stock's idiosyncratic swings.
              </td>
            </tr>
            <tr>
              <td className="mono">≥ 2.0</td>
              <td>
                <span className="doc-pill pill-high">News-driven</span>
              </td>
              <td>
                Idiosyncratic moves concentrate hard on news days — the stock
                trades on its headlines.
              </td>
            </tr>
          </tbody>
        </table>
        <p className="muted">
          Example: a News Beta of 1.8 means the stock's market-adjusted moves are
          on average 1.8× larger on days it's in the news than on days it isn't.
        </p>
      </section>

      <section className="panel doc-section">
        <h3>Guardrails before we issue a verdict</h3>
        <ul className="doc-list">
          <li>
            <strong>Minimum sample:</strong> at least 5 aligned news days and 20
            quiet days in the window — otherwise the app says "Not enough data"
            instead of guessing.
          </li>
          <li>
            <strong>Top-10 moves explained:</strong> shown alongside the score —
            the share of the ticker's 10 largest abnormal-move days that had
            aligned coverage. A high News Beta with a low top-10 hit rate means
            the biggest moves happened <em>without</em> news, which weakens the
            story.
          </li>
          <li>
            <strong>Method validation:</strong> the metric was first tested on a
            50-stock basket, checking that rankings stay stable across
            split-half samples and that the score relates to things investors
            feel — drawdowns, risk-adjusted returns, and recovery time after
            news-day drops (see <span className="mono">research/</span> in the
            repo).
          </li>
        </ul>
      </section>

      <section className="panel doc-section">
        <h3>Honest limitations</h3>
        <ul className="doc-list">
          <li>
            <strong>Correlational, not causal.</strong> News Beta says moves and
            coverage coincide; it cannot prove the article caused the move.
            Outlets also write <em>about</em> big moves after they happen —
            recap-style coverage inflates the association.
          </li>
          <li>
            <strong>Free news feeds skew recent and incomplete.</strong> Thinly
            covered small-caps may show "Not enough data" or an unstable score.
          </li>
          <li>
            <strong>The score is window-dependent.</strong> A stock through an
            earnings-heavy quarter will score hotter than the same stock in a
            quiet stretch. Compare like-for-like periods.
          </li>
          <li>
            <strong>Not investment advice.</strong> It's a lens on volatility
            character, not a buy/sell signal.
          </li>
        </ul>
      </section>
    </div>
  );
}
