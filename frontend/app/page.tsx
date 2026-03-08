"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Search,
  Heart,
  Package,
  CreditCard,
  Truck,
  RotateCcw,
  ShieldCheck,
  Star,
} from "lucide-react";
import { getProducts, Product } from "@/lib/api";

/* ── animation helpers ─────────────────────────────────────────────────── */
const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.12, duration: 0.5 },
  }),
};

/* ── HERO ──────────────────────────────────────────────────────────────── */
function Hero() {
  return (
    <section className="relative overflow-hidden bg-navy text-white">
      <div className="mx-auto flex max-w-7xl flex-col-reverse lg:flex-row items-center gap-10 px-6 py-20 lg:py-28">
        {/* Left copy */}
        <motion.div
          initial={{ opacity: 0, x: -40 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.7 }}
          className="flex-1 text-center lg:text-left"
        >
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold leading-tight">
            Elevate Your
            <br />
            <span className="text-gold">Style Journey</span>
          </h1>

          <p className="mt-5 max-w-lg text-lg text-white/70 mx-auto lg:mx-0">
            Meet Aria — your AI-powered personal shopper who knows your taste,
            remembers your preferences, and finds exactly what you need.
          </p>

          <div className="mt-8 flex flex-wrap gap-4 justify-center lg:justify-start">
            <Link
              href="/chat"
              className="rounded-full bg-gold px-7 py-3 font-semibold text-navy hover:bg-gold-light transition-colors"
            >
              Chat with Aria
            </Link>
            <Link
              href="/products"
              className="rounded-full border border-white/40 px-7 py-3 font-semibold text-white hover:bg-white/10 transition-colors"
            >
              Browse Products
            </Link>
          </div>
        </motion.div>

        {/* Right abstract shape */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="flex-1 flex justify-center"
        >
          <div className="relative w-64 h-80 lg:w-80 lg:h-96">
            {/* Abstract geometric fashion silhouette */}
            <div className="absolute inset-0 rounded-3xl bg-gold/20 rotate-6" />
            <div className="absolute inset-4 rounded-3xl bg-gold/30 -rotate-3" />
            <div className="absolute inset-8 rounded-3xl bg-gold/40 rotate-2 flex items-center justify-center">
              <div className="text-center">
                <div className="w-16 h-16 mx-auto rounded-full bg-gold/60 mb-3" />
                <div className="w-10 h-24 mx-auto rounded-t-full bg-gold/50" />
                <div className="w-20 h-16 mx-auto rounded-b-3xl bg-gold/40 -mt-1" />
              </div>
            </div>
            {/* Sparkle accents */}
            <div className="absolute top-4 right-4 w-3 h-3 bg-gold rounded-full animate-pulse" />
            <div className="absolute bottom-8 left-2 w-2 h-2 bg-gold rounded-full animate-pulse" />
            <div className="absolute top-1/3 -right-2 w-2 h-2 bg-gold-light rounded-full animate-pulse" />
          </div>
        </motion.div>
      </div>
    </section>
  );
}

/* ── FEATURES STRIP ────────────────────────────────────────────────────── */
const features = [
  {
    icon: Search,
    title: "AI-Powered Search",
    desc: "Describe what you want in natural language and get perfect matches.",
  },
  {
    icon: Heart,
    title: "Remembers Your Style",
    desc: "Aria learns your preferences with every conversation.",
  },
  {
    icon: Package,
    title: "Real-Time Inventory",
    desc: "Never see out-of-stock items — only what you can actually buy.",
  },
  {
    icon: CreditCard,
    title: "Seamless Checkout",
    desc: "Pay in one click with your preferred payment method.",
  },
];

function FeaturesStrip() {
  return (
    <section className="bg-white py-16">
      <div className="mx-auto max-w-7xl px-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, amount: 0.3 }}
            custom={i}
            className="rounded-xl border border-border bg-white p-6 text-center shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-navy/5">
              <f.icon className="h-6 w-6 text-gold" />
            </div>
            <h3 className="text-base font-bold text-navy">{f.title}</h3>
            <p className="mt-2 text-sm text-muted">{f.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

/* ── FEATURED PRODUCTS ─────────────────────────────────────────────────── */
function SkeletonCard() {
  return (
    <div className="rounded-xl border border-border p-4 space-y-3">
      <div className="skeleton h-40 w-full rounded-lg" />
      <div className="skeleton h-4 w-3/4" />
      <div className="skeleton h-3 w-1/2" />
      <div className="skeleton h-8 w-24 rounded-full" />
    </div>
  );
}

function Stars({ rating }: { rating: number }) {
  return (
    <div className="flex gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={`h-3.5 w-3.5 ${i < Math.round(rating)
              ? "fill-gold text-gold"
              : "fill-border text-border"
            }`}
        />
      ))}
    </div>
  );
}

const categoryColors: Record<string, string> = {
  "Ethnic Wear": "bg-navy/10 text-navy",
  "Western Wear": "bg-gold/15 text-navy",
  Accessories: "bg-sage/15 text-sage",
  Footwear: "bg-coral/15 text-coral",
};

function ProductCard({ product }: { product: Product }) {
  return (
    <motion.div
      whileHover={{ y: -4, boxShadow: "0 8px 30px rgba(30,39,97,0.10)" }}
      transition={{ type: "spring", stiffness: 300 }}
      className="rounded-xl border border-border bg-white p-4 flex flex-col"
    >
      {/* image placeholder */}
      <div className="h-44 rounded-lg bg-gradient-to-br from-navy/5 to-gold/10 flex items-center justify-center text-3xl select-none">
        {product.category === "Footwear"
          ? "👟"
          : product.category === "Accessories"
            ? "👜"
            : product.category === "Western Wear"
              ? "👗"
              : "🥻"}
      </div>

      <div className="mt-3 flex-1 space-y-1.5">
        <span
          className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${categoryColors[product.category] ?? "bg-navy/10 text-navy"
            }`}
        >
          {product.category}
        </span>
        <h4 className="text-sm font-semibold text-navy line-clamp-1">
          {product.name}
        </h4>
        <Stars rating={product.rating ?? 4} />
        <p className="text-base font-bold text-navy">
          ₹{product.price.toLocaleString("en-IN")}
        </p>
      </div>

      <Link
        href="/chat"
        className="mt-3 block rounded-full bg-navy px-4 py-2 text-center text-xs font-semibold text-white hover:bg-navy-light transition-colors"
      >
        Add to Chat
      </Link>
    </motion.div>
  );
}

function FeaturedProducts() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProducts()
      .then((res) => setProducts(res.products.slice(0, 6)))
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="py-16 bg-white">
      <div className="mx-auto max-w-7xl px-6">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-2xl font-bold text-navy">Featured Products</h2>
          <Link
            href="/products"
            className="text-sm font-medium text-gold hover:text-gold-light transition-colors"
          >
            See All →
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {loading
            ? Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)
            : products.map((p) => <ProductCard key={p.id} product={p} />)}
        </div>
      </div>
    </section>
  );
}

/* ── SHOP BY CATEGORY ──────────────────────────────────────────────────── */
const categories = [
  { name: "Ethnic Wear", emoji: "🥻", bg: "bg-navy", text: "text-white" },
  { name: "Western Wear", emoji: "👗", bg: "bg-gold", text: "text-navy" },
  { name: "Accessories", emoji: "👜", bg: "bg-sage", text: "text-white" },
  { name: "Footwear", emoji: "👟", bg: "bg-coral", text: "text-white" },
];

function ShopByCategory() {
  return (
    <section className="py-16 bg-navy/[0.02]">
      <div className="mx-auto max-w-7xl px-6">
        <h2 className="text-2xl font-bold text-navy mb-8 text-center">
          Shop By Category
        </h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
          {categories.map((c, i) => (
            <motion.div
              key={c.name}
              variants={fadeUp}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              custom={i}
              whileHover={{ scale: 1.04 }}
            >
              <Link
                href={`/products?category=${encodeURIComponent(c.name)}`}
                className={`${c.bg} ${c.text} flex flex-col items-center justify-center rounded-2xl py-10 px-4 shadow-sm hover:shadow-md transition-shadow`}
              >
                <span className="text-4xl mb-3">{c.emoji}</span>
                <span className="text-lg font-bold">{c.name}</span>
                <span className="mt-1 text-sm opacity-70">View →</span>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ── TRUST BAR ─────────────────────────────────────────────────────────── */
const trustItems = [
  {
    icon: Truck,
    title: "Free Delivery",
    desc: "Free shipping on orders above ₹999",
  },
  {
    icon: RotateCcw,
    title: "Easy Returns",
    desc: "15-day hassle-free return policy",
  },
  {
    icon: ShieldCheck,
    title: "Secure Payment",
    desc: "100% encrypted & verified transactions",
  },
];

function TrustBar() {
  return (
    <section className="bg-border/30 py-12">
      <div className="mx-auto max-w-5xl px-6 grid grid-cols-1 sm:grid-cols-3 gap-8 text-center">
        {trustItems.map((t, i) => (
          <motion.div
            key={t.title}
            variants={fadeUp}
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            custom={i}
            className="flex flex-col items-center"
          >
            <t.icon className="h-8 w-8 text-navy mb-3" />
            <h4 className="text-sm font-bold text-navy">{t.title}</h4>
            <p className="mt-1 text-xs text-muted">{t.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

/* ── PAGE ──────────────────────────────────────────────────────────────── */
export default function HomePage() {
  return (
    <>
      <Hero />
      <FeaturesStrip />
      <FeaturedProducts />
      <ShopByCategory />
      <TrustBar />
    </>
  );
}
