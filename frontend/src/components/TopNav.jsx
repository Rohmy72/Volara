export default function TopNav() {
  return (
    <header className="topnav">
      <a className="brand" href="#/" aria-label="Volara home">
        <span className="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 32 32" width="30" height="30" role="img" aria-label="Volara logo">
            <defs>
              <linearGradient id="volaraGrad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stopColor="#d95f38" />
                <stop offset="100%" stopColor="#f4a07d" />
              </linearGradient>
            </defs>
            <rect x="1.5" y="1.5" width="29" height="29" rx="9" fill="url(#volaraGrad)" />
            {/* volatility pulse line */}
            <path
              d="M6 20 L11 20 L14 11 L18 24 L21 15 L26 15"
              fill="none"
              stroke="#12253a"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </span>
        <span className="brand-text">
          <span className="brand-name">Volara</span>
          <span className="brand-tag">news volatility intelligence</span>
        </span>
      </a>

      <div className="topnav-right">
        <span className="live-pill">
          <span className="live-dot" aria-hidden="true" />
          Live data
        </span>
        <a className="nav-link" href="#/news-beta">
          What is News Beta?
        </a>
      </div>
    </header>
  );
}
