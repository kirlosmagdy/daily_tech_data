import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
});

export const metadata = {
  title: "Daily Tech & Data Pulse",
  description: "Daily curated feed across Data Engineering, AI/ML, Databases, Cloud, and Open Source.",
};

// Render the minimal root layout with a single self-hosted font.
export default function RootLayout({ children }) {
  return (
    <html lang="en" className={inter.className}>
      <body>{children}</body>
    </html>
  );
}