// Render the About and Methodology documentation page with attribution and repository link.
export default function AboutPage() {
  return (
    <div className="card-list">
      <div className="card">
        <h1 className="section-title">About &amp; Methodology</h1>
        <p className="snippet">
          <strong>Daily Tech &amp; Data Pulse</strong> is an automated daily data engineering pipeline and static analytics site. Every day, it extracts new items from trusted engineering sources, normalizes and deduplicates URLs into a 90-day Parquet history, enriches content with topics, tool mentions, and VADER sentiment, transforms Gold tables via <code>dbt-duckdb</code>, and publishes a static Next.js build.
        </p>
      </div>

      <div className="card">
        <h2 className="section-title">Ranking Formula &amp; Honesty Rule</h2>
        <p className="snippet">
          <strong>Rank Score</strong> = <code>engagement_percentile × trust_weight × freshness_decay × cross_source_bonus</code>.
        </p>
        <p className="snippet">
          Engagement percentile compares each item against items from the same source over the last 7 days using <code>points + 2 × comments</code> (sources without engagement metrics, such as RSS and arXiv, receive a fixed 0.7 percentile). Freshness halves every 18 hours. Items appearing across multiple sources earn +15% per additional source (up to +45%).
        </p>
        <p className="snippet">
          <strong>Honesty &amp; Attribution Policy:</strong> This site never claims an item is &quot;verified true&quot; and never stores full article text. Every card displays at most a 300-character snippet, attributes the source and its trust tier, and links directly to the original author URL.
        </p>
      </div>

      <div className="card">
        <h2 className="section-title">Source Code &amp; Attribution</h2>
        <p className="snippet">
          Data is collected politely from Hacker News (Algolia API), dev.to, Lobsters, 15 official engineering RSS feeds, GitHub Search API, arXiv API, and Hugging Face Daily Papers.
        </p>
        <a
          href="https://github.com/kirlosmagdy/daily_tech_data"
          target="_blank"
          rel="noopener noreferrer"
          className="badge badge-accent"
        >
          View Repository on GitHub ↗
        </a>
      </div>
    </div>
  );
}