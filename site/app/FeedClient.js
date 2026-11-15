"use client";
import { useMemo, useState } from "react";

// Render interactive filters, search bar, and ranked item cards for the Today page.
export default function FeedClient({ items }) {
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [topicFilter, setTopicFilter] = useState("all");
  const [sortBy, setSortBy] = useState("rank");

  const sources = useMemo(() => Array.from(new Set(items.map((i) => i.source))).sort(), [items]);
  const topics = useMemo(
    () => Array.from(new Set(items.flatMap((i) => i.topics || []))).sort(),
    [items]
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items
      .filter((item) => {
        if (sourceFilter !== "all" && item.source !== sourceFilter) return false;
        if (topicFilter !== "all" && !(item.topics || []).includes(topicFilter)) return false;
        if (q && !`${item.title} ${item.snippet || ""}`.toLowerCase().includes(q)) return false;
        return true;
      })
      .sort((a, b) => {
        if (sortBy === "newest") {
          return new Date(b.published_at).getTime() - new Date(a.published_at).getTime();
        }
        return (b.rank_score || 0) - (a.rank_score || 0);
      });
  }, [items, search, sourceFilter, topicFilter, sortBy]);

  return (
    <div>
      <section className="controls" aria-label="Feed Filters">
        <input
          type="search"
          className="input-box"
          placeholder="Search title or snippet..."
          aria-label="Search articles"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="select-box"
          aria-label="Filter by source"
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
        >
          <option value="all">All Sources ({items.length})</option>
          {sources.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          className="select-box"
          aria-label="Filter by topic"
          value={topicFilter}
          onChange={(e) => setTopicFilter(e.target.value)}
        >
          <option value="all">All Topics</option>
          {topics.map((t) => (
            <option key={t} value={t}>{t.replaceAll("_", " ")}</option>
          ))}
        </select>
        <select
          className="select-box"
          aria-label="Sort items"
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          <option value="rank">Sort: Top Ranked</option>
          <option value="newest">Sort: Newest First</option>
        </select>
      </section>

      {filtered.length === 0 ? (
        <div className="card">No items match your current filters.</div>
      ) : (
        <div className="card-list">
          {filtered.map((item) => {
            const alsoSeen = (item.mentioned_in_sources || []).filter((s) => s !== item.source);
            const pubTime = item.published_at ? item.published_at.replace("T", " ").slice(0, 16) + " UTC" : "";
            return (
              <article key={item.canonical_url} className="card">
                <a
                  href={item.canonical_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="card-title"
                >
                  {item.title} ↗
                </a>
                <div className="card-meta">
                  <span className="badge badge-accent">
                    {item.source} · {item.tier.replace("_", " ").toUpperCase()}
                  </span>
                  <span>Rank: {Number(item.rank_score).toFixed(3)}</span>
                  <span>Score: {item.source_score}</span>
                  <span>{pubTime}</span>
                  {alsoSeen.length > 0 && (
                    <span className="badge">Also seen on: {alsoSeen.join(", ")}</span>
                  )}
                </div>
                {item.snippet && <p className="snippet">{item.snippet}</p>}
                <div className="card-meta">
                  {(item.topics || []).map((t) => (
                    <span key={t} className="badge">{t.replaceAll("_", " ")}</span>
                  ))}
                  {(item.tools_mentioned || []).map((tl) => (
                    <span key={tl} className="badge badge-accent">🛠 {tl}</span>
                  ))}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}