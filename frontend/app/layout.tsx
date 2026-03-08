import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Aria — Your AI Shopping Assistant",
  description:
    "Premium AI-powered retail experience. Chat with Aria to discover, explore and shop curated fashion.",
};

/* ── Navbar ─────────────────────────────────────────────────────────────── */
function Navbar() {
  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-border">
      <nav className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-1.5 select-none">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#C9A84C"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 3l1.912 5.813a2 2 0 001.272 1.272L21 12l-5.813 1.912a2 2 0 00-1.272 1.272L12 21l-1.912-5.813a2 2 0 00-1.272-1.272L3 12l5.813-1.912a2 2 0 001.272-1.272L12 3z" />
          </svg>
          <span className="text-xl font-bold tracking-tight text-navy">
            ARIA
          </span>
        </Link>

        {/* Links */}
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-navy">
          <Link href="/" className="hover:text-gold transition-colors">
            Home
          </Link>
          <Link
            href="/products"
            className="hover:text-gold transition-colors"
          >
            Products
          </Link>
          <Link href="/chat" className="hover:text-gold transition-colors">
            Chat with Aria
          </Link>
          <Link href="/orders" className="hover:text-gold transition-colors">
            Orders
          </Link>
        </div>

        {/* CTA */}
        <Link
          href="/chat"
          className="rounded-full bg-gold px-5 py-2 text-sm font-semibold text-navy shadow-sm hover:bg-gold-light transition-colors"
        >
          Chat Now
        </Link>
      </nav>
    </header>
  );
}

/* ── Footer ─────────────────────────────────────────────────────────────── */
function Footer() {
  return (
    <footer className="border-t border-border bg-navy text-white">
      <div className="mx-auto max-w-7xl px-6 py-10 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="text-center md:text-left">
          <span className="text-lg font-bold tracking-tight">ARIA</span>
          <p className="mt-1 text-sm text-white/60">
            Your AI-powered personal shopping assistant
          </p>
        </div>
        <p className="text-xs text-white/40">
          &copy; {new Date().getFullYear()} Aria Retail. All rights reserved.
        </p>
      </div>
    </footer>
  );
}

/* ── Root Layout ────────────────────────────────────────────────────────── */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        <Navbar />
        <main className="min-h-screen">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
