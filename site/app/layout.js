import "./globals.css";
import Link from "next/link";
import fs from "fs";
import path from "path";
import StaleBanner from "./StaleBanner";

export const metadata = {
  title: "Daily Tech & Data Pulse",
  description: "Automated daily intelligence across Data Engineering, AI/ML, Databases, and Open Source.",
};

// Load pipeline metadata JSON at build time for header statistics.
function getMeta() {
  try {
    const filePath = path.join(process.cwd(), "data", "meta.json");
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return { generated_at: null, today_count: 0, sources_ok: 0, sources_total: 7 };
  }
}

// Render the root application layout with navigation and client-side freshness check.
export default function RootLayout({ children }) {
  const meta = getMeta();

  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0D0B09] text-stone-100 antialiased">
        <StaleBanner generatedAt={meta.generated_at} />
        <header className="border-b border-stone-800 bg-[#14110E]">
          <div className="max-w-6xl mx-auto px-4 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <Link href="/" className="text-xl font-bold tracking-tight text-[#F5B700]">
                Daily Tech &amp; Data Pulse
              </Link>
              <p className="text-xs text-stone-400 mt-0.5">
                Last updated: {meta.generated_at ? meta.generated_at : "N/A"} &bull; Sources OK:{" "}
                {meta.sources_ok}/{meta.sources_total}
              </p>
            </div>
            <nav className="flex flex-wrap gap-4 text-sm font-medium text-stone-300">
              <Link href="/" className="hover:text-[#F5B700] transition-colors">Today</Link>
              <Link href="/trends" className="hover:text-[#F5B700] transition-colors">Trends</Link>
              <Link href="/sentiment" className="hover:text-[#F5B700] transition-colors">Sentiment</Link>
              <Link href="/sources" className="hover:text-[#F5B700] transition-colors">Sources</Link>
              <Link href="/about" className="hover:text-[#F5B700] transition-colors">About</Link>
            </nav>
          </div>
        </header>
        <main className="max-w-6xl mx-auto px-4 py-6">{children}</main>
      </body>
    </html>
  );
}