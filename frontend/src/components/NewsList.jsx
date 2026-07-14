export default function NewsList({ news }) {
  return (
    <div className="panel">
      <h3>Recent news ({news.length})</h3>
      <ul className="news-list">
        {news.map((item, i) => (
          <li key={i}>
            <a href={item.url} target="_blank" rel="noopener noreferrer">
              {item.title}
            </a>
            <div className="news-meta">
              <span>{item.source}</span>
              <span>{new Date(item.published_at).toLocaleDateString()}</span>
              {item.matched_trading_day && (
                <span className="news-tag">aligned to {item.matched_trading_day}</span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
