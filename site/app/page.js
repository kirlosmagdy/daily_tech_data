import fs from "fs";
import path from "path";
import FeedClient from "./FeedClient";

// Read a JSON file from site/data at build time with a safe fallback.
function readData(filename, fallback) {
  try {
    const filePath = path.join(process.cwd(), "data", filename);
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch {
    return fallback;
  }
}

// Render the single-page feed from build-time static data.
export default function HomePage() {
  const items = readData("today.json", []);
  const sources = readData("sources.json", []);
  const meta = readData("meta.json", {
    project: "Daily Tech & Data Pulse",
    generated_at: null,
  });

  return <FeedClient items={items} sources={sources} meta={meta} />;
}