"use client";

// Render lightweight visual bar charts for 30-day topic volume and tool mentions.
export default function TrendsCharts({ topicTotals, tools }) {
  const maxTopic = Math.max(...topicTotals.map((t) => t.total), 1);
  const maxTool = Math.max(...tools.map((t) => t.mentions_last_7d), 1);

  return (
    <div className="grid-2">
      <div className="card">
        <h2 className="section-title">Topic Volume (Last 30 Days)</h2>
        <div className="card-list">
          {topicTotals.map((t) => (
            <div key={t.topic}>
              <div className="header-inner" style={{ marginBottom: "0.25rem", fontSize: "0.86rem" }}>
                <span>{t.topic.replaceAll("_", " ")}</span>
                <strong>{t.total} items</strong>
              </div>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${Math.round((t.total / maxTopic) * 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <h2 className="section-title">Top Tools Mentioned (Last 7 Days)</h2>
        <div className="card-list">
          {tools.slice(0, 12).map((tl) => (
            <div key={tl.tool}>
              <div className="header-inner" style={{ marginBottom: "0.25rem", fontSize: "0.86rem" }}>
                <span>{tl.tool}</span>
                <span>
                  <strong>{tl.mentions_last_7d}</strong> (Δ {tl.mentions_delta >= 0 ? `+${tl.mentions_delta}` : tl.mentions_delta})
                </span>
              </div>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${Math.round((tl.mentions_last_7d / maxTool) * 100)}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}