import sentimentData from "../../data/sentiment.json";
import toolsData from "../../data/tools.json";

// Render weekly tool discussion sentiment with the required VADER methodology disclaimer.
export default function SentimentPage() {
  return (
    <div>
      <h1 className="section-title">Weekly Tool Discussion Sentiment</h1>
      <div className="card" style={{ marginBottom: "1rem" }}>
        <strong>Important Note:</strong> Sentiment is calculated using local rule-based VADER analysis on item titles and snippets (−1.0 to +1.0). It measures the <strong>tone of community discussion</strong>, not product quality. Only tools with at least 10 mentions in a week are shown in the weekly table below.
      </div>

      <h2 className="section-title">Weekly Qualified Tools (≥10 Mentions / Week)</h2>
      <div className="table-wrap" style={{ marginBottom: "1.5rem" }}>
        <table>
          <thead>
            <tr>
              <th>Week Start</th>
              <th>Tool</th>
              <th>Mentions</th>
              <th>Discussion Tone (−1 to +1)</th>
            </tr>
          </thead>
          <tbody>
            {(sentimentData || []).length === 0 ? (
              <tr>
                <td colSpan={4}>No tools have reached ≥10 mentions in a single week yet.</td>
              </tr>
            ) : (
              sentimentData.map((row) => (
                <tr key={`${row.week_start}-${row.tool}`}>
                  <td>{row.week_start}</td>
                  <td><strong>{row.tool}</strong></td>
                  <td>{row.mentions_count}</td>
                  <td>{Number(row.avg_sentiment).toFixed(3)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <h2 className="section-title">7-Day Tool Discussion Tone Overview</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Tool</th>
              <th>7-Day Mentions</th>
              <th>Avg Discussion Tone</th>
            </tr>
          </thead>
          <tbody>
            {(toolsData || []).map((t) => (
              <tr key={t.tool}>
                <td><strong>{t.tool}</strong></td>
                <td>{t.mentions_last_7d}</td>
                <td>{t.avg_sentiment_7d !== null ? Number(t.avg_sentiment_7d).toFixed(3) : "0.000"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}