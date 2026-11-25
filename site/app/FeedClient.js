"use client";

import { useEffect, useMemo, useState } from "react";

const SOURCE_LABELS = {
  medium: "Medium",
  daily_dev: "daily.dev",
  devbytes: "DevBytes",
  x: "X",
  reddit: "Reddit",
  hackernews: "HN",
  devto: "dev.to",
  lobsters: "Lobsters",
  rss: "RSS",
  github: "GitHub",
  arxiv: "arXiv",
  hf_papers: "HF Papers",
};

const TOPIC_LABELS = {
  data_engineering: "Data Engineering",
  analytics_and_bi: "Analytics & BI",
  databases_and_warehouses: "Databases",
  ai_and_ml: "AI & ML",
  programming_and_devtools: "Dev & Tools",
  cloud: "Cloud",
  security: "Security",
  open_source: "Open Source",
};

// Convert a source slug to its display label.
function sourceLabel(slug) {
  return SOURCE_LABELS[slug] || slug;
}

// Convert a topic slug to a clean human-readable label.
function topicLabel(slug) {
  return TOPIC_LABELS[slug] || slug.replace(/_/g, " ");
}

// Return the YYYY-MM-DD local calendar key for a Date object.
function dayKey(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

// Format a day group heading as Today, Yesterday, or a readable date.
function dayHeading(key, now) {
  const today = dayKey(now);
  const yesterdayDate = new Date(now);
  yesterdayDate.setDate(now.getDate() - 1);
  const yesterday = dayKey(yesterdayDate);

  if (key === today) return "Today";
  if (key === yesterday) return "Yesterday";
  const [y, m, d] = key.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

// Format a timestamp for card display (time only when grouped by day, or date + time in Top mode).
function formatTime(iso, includeDate) {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return "";
  if (includeDate) {
    return dt.toLocaleString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }
  return dt.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

// Format the header "Last updated" timestamp.
function formatUpdated(iso) {
  if (!iso) return "Unknown";
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) return iso;
  return dt.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Render the interactive single-page feed with header health dots, filters, and day grouping.
export default function FeedClient({ items, sources, meta }) {
  const [query, setQuery] = useState("");
  const [selectedSource, setSelectedSource] = useState("all");
  const [selectedTopic, setSelectedTopic] = useState("all");
  const [sortBy, setSortBy] = useState("newest");
  const [now, setNow] = useState(() => (meta.generated_at ? new Date(meta.generated_at) : new Date()));

  useEffect(() => {
    setNow(new Date());
  }, []);

  const isStale = useMemo(() => {
    if (!meta.generated_at) return false;
    const diffHours = (now.getTime() - new Date(meta.generated_at).getTime()) / (1000 * 60 * 60);
    return diffHours > 36;
  }, [meta.generated_at, now]);

  const sourceOptions = useMemo(() => {
    const counts = {};
    for (const item of items) {
      counts[item.source] = (counts[item.source] || 0) + 1;
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [items]);

  const topicOptions = useMemo(() => {
    const set = new Set();
    for (const item of items) {
      for (const t of item.topics || []) set.add(t);
    }
    return Array.from(set).sort();
  }, [items]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = items.filter((item) => {
      if (selectedSource !== "all" && item.source !== selectedSource) return false;
      if (selectedTopic !== "all" && !(item.topics || []).includes(selectedTopic)) return false;
      if (q) {
        const hay = `${item.title || ""} ${item.snippet || ""} ${item.source || ""} ${(item.topics || []).join(" ")}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    return [...list].sort((a, b) => {
      if (sortBy === "top") {
        return (b.rank_score || 0) - (a.rank_score || 0);
      }
      return new Date(b.published_at).getTime() - new Date(a.published_at).getTime();
    });
  }, [items, query, selectedSource, selectedTopic, sortBy]);

  const groupedByDay = useMemo(() => {
    if (sortBy !== "newest") return [];
    const groups = new Map();
    for (const item of filtered) {
      const dt = new Date(item.published_at);
      const key = Number.isNaN(dt.getTime()) ? "Unknown" : dayKey(dt);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    }
    return Array.from(groups.entries());
  }, [filtered, sortBy]);

  return (
    <div className="page">
      <header className="header">
        <div className="header-top">
          <h1 className="brand">{meta.project || "Daily Tech & Data Pulse"}</h1>
          <div className="health-dots" aria-label="Source health status">
            {sources.map((s) => {
              const st = s.status || "failed";
              const count = s.last_run_count ?? s.item_count ?? 0;
              const tip = `${sourceLabel(s.source)}: ${st} (${count} items)`;
              return (
                <span
                  key={s.source}
                  className={`dot dot-${st}`}
                  title={tip}
                  aria-label={tip}
                />
              );
            })}
          </div>
        </div>
        <p className={`updated ${isStale ? "updated-stale" : ""}`}>
          Last updated: {formatUpdated(meta.generated_at)}
          {isStale ? " (stale)" : ""} &middot; {filtered.length} items
        </p>
      </header>

      <section className="controls" aria-label="Filter and sort feed">
        <div className="search-row">
          <input
            type="search"
            className="search-input"
            placeholder="Search titles, snippets, topics..."
            aria-label="Search feed"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <div className="sort-switch" role="group" aria-label="Sort order">
            <button
              type="button"
              className={`sort-btn ${sortBy === "newest" ? "active" : ""}`}
              onClick={() => setSortBy("newest")}
            >
              Newest
            </button>
            <button
              type="button"
              className={`sort-btn ${sortBy === "top" ? "active" : ""}`}
              onClick={() => setSortBy("top")}
            >
              Top
            </button>
          </div>
        </div>

        <div className="chip-row" aria-label="Filter by source">
          <button
            type="button"
            className={`chip ${selectedSource === "all" ? "active" : ""}`}
            onClick={() => setSelectedSource("all")}
          >
            All sources
          </button>
          {sourceOptions.map(([src, count]) => (
            <button
              key={src}
              type="button"
              className={`chip ${selectedSource === src ? "active" : ""}`}
              onClick={() => setSelectedSource(src)}
            >
              {sourceLabel(src)} <span className="chip-count">{count}</span>
            </button>
          ))}
        </div>

        <div className="chip-row" aria-label="Filter by topic">
          <button
            type="button"
            className={`chip ${selectedTopic === "all" ? "active" : ""}`}
            onClick={() => setSelectedTopic("all")}
          >
            All topics
          </button>
          {topicOptions.map((topic) => (
            <button
              key={topic}
              type="button"
              className={`chip ${selectedTopic === topic ? "active" : ""}`}
              onClick={() => setSelectedTopic(topic)}
            >
              {topicLabel(topic)}
            </button>
          ))}
        </div>
      </section>

      <main className="feed">
        {filtered.length === 0 ? (
          <p className="empty">No items match the current filters.</p>
        ) : sortBy === "newest" ? (
          groupedByDay.map(([key, dayItems]) => (
            <section key={key} className="day-group">
              <h2 className="day-heading">{key === "Unknown" ? "Undated" : dayHeading(key, now)}</h2>
              <div className="card-list">
                {dayItems.map((item) => (
                  <FeedCard key={item.canonical_url} item={item} showDate={false} />
                ))}
              </div>
            </section>
          ))
        ) : (
          <section className="day-group">
            <h2 className="day-heading">Top ranked (last 7 days)</h2>
            <div className="card-list">
              {filtered.map((item) => (
                <FeedCard key={item.canonical_url} item={item} showDate={true} />
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

// Render a single article card with source badge, timestamp, snippet, topics, and cross-source note.
function FeedCard({ item, showDate }) {
  const alsoOn = (item.mentioned_in_sources || []).filter((s) => s !== item.source);

  return (
    <article className="card">
      <div className="card-meta">
        <span className={`src-badge src-${item.source}`}>{sourceLabel(item.source)}</span>
        <time className="card-time" dateTime={item.published_at}>
          {formatTime(item.published_at, showDate)}
        </time>
        {alsoOn.length > 0 && (
          <span className="also-on">also on {alsoOn.map(sourceLabel).join(", ")}</span>
        )}
      </div>

      <h3 className="card-title">
        <a href={item.canonical_url} target="_blank" rel="noopener noreferrer">
          {item.title}
        </a>
      </h3>

      {item.snippet && <p className="card-snippet">{item.snippet}</p>}

      {item.topics && item.topics.length > 0 && (
        <div className="card-topics">
          {item.topics.map((t) => (
            <span key={t} className="topic-tag">
              {topicLabel(t)}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}