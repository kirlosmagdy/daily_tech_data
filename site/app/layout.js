import "./globals.css";
import Link from "next/link";
import ThemeToggle from "./ThemeToggle";
import meta from "../data/meta.json";

export const metadata = {
  title: "Daily Tech Data",
  description: "Daily ranked feed and analytics of tech and data engineering content.",
};

// Render the global navigation header, last updated timestamp, and page container.
export default function RootLayout({ children }) {
  const updatedDate = meta?.generated_at ? new Date(meta.generated_at) : null;
  const updatedStr = updatedDate ? updatedDate.toISOString().replace("T", " ").slice(0, 16) + " UTC" : "Unknown";
  const ageHours = updatedDate ? (Date.now() - updatedDate.getTime()) / 3600000 : 0;
  const isStale = ageHours > 36;

  return (
    <html lang="en" data-theme="dark">
      <body>
        <header className="site-header">
          <div className="container header-inner">
            <div>
              <Link href="/" className="brand-title">
                Daily Tech &amp; Data Pulse
              </Link>
              <div className="meta-sub">Last updated: {updatedStr}</div>
            </div>
            <nav className="nav-links" aria-label="Main Navigation">
              <Link href="/">Today</Link>
              <Link href="/trends">Trends</Link>
              <Link href="/sentiment">Sentiment</Link>
              <Link href="/sources">Sources</Link>
              <Link href="/about">About</Link>
              <ThemeToggle />
            </nav>
          </div>
        </header>
        <main className="container">
          {isStale && (
            <div className="stale-banner" role="alert">
              Warning: Pipeline data is more than 36 hours old (last updated {updatedStr}).
            </div>
          )}
          {children}
        </main>
      </body>
    </html>
  );
}