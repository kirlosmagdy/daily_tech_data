"use client";

import { useEffect, useState } from "react";

// Display a warning banner in the browser when generated_at is older than 36 hours.
export default function StaleBanner({ generatedAt }) {
  const [isStale, setIsStale] = useState(false);

  useEffect(() => {
    if (!generatedAt) return;
    const ageHours = (Date.now() - new Date(generatedAt).getTime()) / (1000 * 60 * 60);
    setIsStale(ageHours > 36);
  }, [generatedAt]);

  if (!isStale) return null;

  return (
    <div className=" stale-banner bg-amber-950/80 border-b border-amber-700/60 text-amber-200 text-xs py-2 px-4 text-center">
      Data warning: The latest pipeline snapshot ({generatedAt}) is more than 36 hours old.
    </div>
  );
}