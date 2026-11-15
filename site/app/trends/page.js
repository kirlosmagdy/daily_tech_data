import dynamic from "next/dynamic";
import trendsData from "../../data/trends.json";
import toolsData from "../../data/tools.json";

const TrendsCharts = dynamic(() => import("./TrendsCharts"), { ssr: false });

// Aggregate 30-day topic counts and render the Trends and Biggest Risers page.
export default function TrendsPage() {
  const totalsMap = {};
  for (const row of trendsData || []) {
    totalsMap[row.topic] = (totalsMap[row.topic] || 0) + Number(row.item_count || 0);
  }
  const topicTotals = Object.entries(totalsMap)
    .map(([topic, total]) => ({ topic, total }))
    .sort((a, b) => b.total - a.total);

  const risers = [...(toolsData || [])].sort((a, b) => b.mentions_delta - a.mentions_delta);

  return (
    <div>
      <h1 className="section-title">Trends &amp; Tool Mentions (30 Days)</h1>
      <TrendsCharts topicTotals={topicTotals} tools={toolsData || []} />

      <h2 className="section-title">Biggest Tool Risers (Last 7d vs Prior 7d)</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Tool</th>
              <th>Last 7 Days</th>
              <th>Prior 7 Days</th>
              <th>7-Day Change</th>
            </tr>
          </thead>
          <tbody>
            {risers.map((t) => (
              <tr key={t.tool}>
                <td><strong>{t.tool}</strong></td>
                <td>{t.mentions_last_7d}</td>
                <td>{t.mentions_prev_7d}</td>
                <td>{t.mentions_delta >= 0 ? `+${t.mentions_delta}` : t.mentions_delta}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}