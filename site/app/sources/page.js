import sourcesData from "../../data/sources.json";

// Render the Sources operational health table and trust tier definitions.
export default function SourcesPage() {
  return (
    <div>
      <h1 className="section-title">Source Health &amp; Trust Tiers</h1>
      <div className="table-wrap" style={{ marginBottom: "1.5rem" }}>
        <table>
          <thead>
            <tr>
              <th>Source</th>
              <th>Trust Tier</th>
              <th>Weight</th>
              <th>Status</th>
              <th>Total Items (90d)</th>
              <th>Last Success (UTC)</th>
            </tr>
          </thead>
          <tbody>
            {(sourcesData || []).map((s) => (
              <tr key={s.source}>
                <td><strong>{s.source}</strong></td>
                <td>{s.tier.replace("_", " ").toUpperCase()}</td>
                <td>{s.trust_weight}</td>
                <td>
                  <span className="badge badge-accent">{s.status.toUpperCase()}</span>
                </td>
                <td>{s.item_count}</td>
                <td>{s.last_success_at ? s.last_success_at.replace("T", " ").slice(0, 16) : "Never"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2 className="section-title">Trust Tier Weights</h2>
        <p className="snippet">
          <strong>Tier 1 (Weight 1.0):</strong> Official company engineering blogs, release notes (RSS), arXiv papers, and Hugging Face Daily Papers.
        </p>
        <p className="snippet">
          <strong>Tier 2 (Weight 0.8):</strong> Curated technical communities (Hacker News, Lobsters) and active GitHub repositories.
        </p>
        <p className="snippet">
          <strong>Tier 3 (Weight 0.6):</strong> Open publishing platforms (dev.to, and optional social connectors).
        </p>
      </div>
    </div>
  );
}