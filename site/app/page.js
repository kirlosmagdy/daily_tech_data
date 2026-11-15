import FeedClient from "./FeedClient";
import todayItems from "../data/today.json";

// Render the Today ranked feed page from build-time JSON data.
export default function TodayPage() {
  return (
    <div>
      <h1 className="section-title">Today&apos;s Ranked Tech &amp; Data Feed</h1>
      <FeedClient items={todayItems || []} />
    </div>
  );
}