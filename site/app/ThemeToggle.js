"use client";
import { useEffect, useState } from "react";

// Toggle between dark and light themes and persist preference in localStorage.
export default function ThemeToggle() {
  const [theme, setTheme] = useState("dark");

  useEffect(() => {
    const saved = localStorage.getItem("pulse_theme") || "dark";
    setTheme(saved);
    document.documentElement.setAttribute("data-theme", saved);
  }, []);

  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem("pulse_theme", next);
    document.documentElement.setAttribute("data-theme", next);
  };

  return (
    <button type="button" onClick={toggle} className="theme-btn" aria-label="Toggle color theme">
      {theme === "dark" ? "☀️ Light" : "🌙 Dark"}
    </button>
  );
}