"use client";

import { useEffect, useState, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Star, SlidersHorizontal, X } from "lucide-react";
import { getProducts, Product } from "@/lib/api";

/* ── category / occasion constants ──────────────────────────────────────── */
const CATEGORIES = ["Ethnic Wear", "Western Wear", "Accessories", "Footwear"];
const OCCASIONS = ["Wedding", "Casual", "Office", "Festive", "Party"];

const categoryColors: Record<string, string> = {
    "Ethnic Wear": "bg-navy/10 text-navy",
    "Western Wear": "bg-gold/15 text-navy",
    Accessories: "bg-sage/15 text-sage",
    Footwear: "bg-coral/15 text-coral",
};

/* ── skeleton ───────────────────────────────────────────────────────────── */
function SkeletonCard() {
    return (
        <div className="rounded-xl border border-border p-4 space-y-3">
            <div className="skeleton h-44 w-full rounded-lg" />
            <div className="skeleton h-4 w-3/4" />
            <div className="skeleton h-3 w-1/2" />
            <div className="skeleton h-3 w-1/3" />
            <div className="skeleton h-9 w-full rounded-full" />
        </div>
    );
}

/* ── stars ───────────────────────────────────────────────────────────────── */
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

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  PRODUCTS CONTENT (needs useSearchParams)                                 */
/* ═══════════════════════════════════════════════════════════════════════════ */
function ProductsContent() {
    const searchParams = useSearchParams();
    const initialCategory = searchParams.get("category") || "";

    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(true);

    /* filters */
    const [selectedCategory, setSelectedCategory] = useState(initialCategory);
    const [selectedOccasion, setSelectedOccasion] = useState("");
    const [minPrice, setMinPrice] = useState("");
    const [maxPrice, setMaxPrice] = useState("");
    const [searchQuery, setSearchQuery] = useState("");
    const [sortBy, setSortBy] = useState<"default" | "price-asc" | "price-desc" | "rating">("default");
    const [showFilters, setShowFilters] = useState(false);

    /* fetch */
    const fetchProducts = useCallback(async () => {
        setLoading(true);
        try {
            const filters: Record<string, string | number> = {};
            if (selectedCategory) filters.category = selectedCategory;
            if (selectedOccasion) filters.occasion = selectedOccasion;
            if (minPrice) filters.min_price = Number(minPrice);
            if (maxPrice) filters.max_price = Number(maxPrice);

            const res = await getProducts(filters as Parameters<typeof getProducts>[0]);
            setProducts(res.products);
        } catch {
            setProducts([]);
        } finally {
            setLoading(false);
        }
    }, [selectedCategory, selectedOccasion, minPrice, maxPrice]);

    useEffect(() => {
        fetchProducts();
    }, [fetchProducts]);

    /* sort + search */
    const displayed = products
        .filter((p) =>
            searchQuery
                ? p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                p.description?.toLowerCase().includes(searchQuery.toLowerCase())
                : true
        )
        .sort((a, b) => {
            if (sortBy === "price-asc") return a.price - b.price;
            if (sortBy === "price-desc") return b.price - a.price;
            if (sortBy === "rating") return (b.rating ?? 0) - (a.rating ?? 0);
            return 0;
        });

    const clearFilters = () => {
        setSelectedCategory("");
        setSelectedOccasion("");
        setMinPrice("");
        setMaxPrice("");
        setSearchQuery("");
        setSortBy("default");
    };

    /* ── Sidebar component ─────────────────────────────────────────────── */
    const FiltersSidebar = (
        <div className="space-y-6">
            {/* Category */}
            <div>
                <h4 className="text-xs font-bold text-navy uppercase tracking-wider mb-3">
                    Category
                </h4>
                <div className="space-y-2">
                    <label className="flex items-center gap-2 text-sm text-navy cursor-pointer">
                        <input
                            type="radio"
                            name="category"
                            checked={!selectedCategory}
                            onChange={() => setSelectedCategory("")}
                            className="accent-gold"
                        />
                        All
                    </label>
                    {CATEGORIES.map((c) => (
                        <label
                            key={c}
                            className="flex items-center gap-2 text-sm text-navy cursor-pointer"
                        >
                            <input
                                type="radio"
                                name="category"
                                checked={selectedCategory === c}
                                onChange={() => setSelectedCategory(c)}
                                className="accent-gold"
                            />
                            {c}
                        </label>
                    ))}
                </div>
            </div>

            {/* Occasion */}
            <div>
                <h4 className="text-xs font-bold text-navy uppercase tracking-wider mb-3">
                    Occasion
                </h4>
                <div className="space-y-2">
                    {OCCASIONS.map((o) => (
                        <label
                            key={o}
                            className="flex items-center gap-2 text-sm text-navy cursor-pointer"
                        >
                            <input
                                type="checkbox"
                                checked={selectedOccasion === o}
                                onChange={() =>
                                    setSelectedOccasion(selectedOccasion === o ? "" : o)
                                }
                                className="accent-gold rounded"
                            />
                            {o}
                        </label>
                    ))}
                </div>
            </div>

            {/* Price */}
            <div>
                <h4 className="text-xs font-bold text-navy uppercase tracking-wider mb-3">
                    Price Range
                </h4>
                <div className="flex gap-2">
                    <input
                        type="number"
                        placeholder="Min"
                        value={minPrice}
                        onChange={(e) => setMinPrice(e.target.value)}
                        className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-gold"
                    />
                    <input
                        type="number"
                        placeholder="Max"
                        value={maxPrice}
                        onChange={(e) => setMaxPrice(e.target.value)}
                        className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-gold"
                    />
                </div>
                <button
                    onClick={fetchProducts}
                    className="mt-2 w-full rounded-full bg-navy py-2 text-xs font-semibold text-white hover:bg-navy-light transition-colors"
                >
                    Apply
                </button>
            </div>

            {/* Clear */}
            <button
                onClick={clearFilters}
                className="text-xs font-medium text-gold hover:text-gold-light transition-colors"
            >
                Clear all filters
            </button>
        </div>
    );

    return (
        <div className="mx-auto max-w-7xl px-6 py-8">
            <div className="flex gap-8">
                {/* Desktop sidebar */}
                <aside className="hidden lg:block w-56 shrink-0">{FiltersSidebar}</aside>

                {/* Main */}
                <div className="flex-1">
                    {/* Search + sort */}
                    <div className="flex flex-col sm:flex-row gap-3 mb-6">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
                            <input
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Search products..."
                                className="w-full rounded-full border border-border bg-white pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-gold/40"
                            />
                        </div>
                        <select
                            value={sortBy}
                            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
                            className="rounded-full border border-border px-4 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-gold"
                        >
                            <option value="default">Sort by</option>
                            <option value="price-asc">Price: Low → High</option>
                            <option value="price-desc">Price: High → Low</option>
                            <option value="rating">Rating</option>
                        </select>
                        <button
                            onClick={() => setShowFilters(!showFilters)}
                            className="lg:hidden flex items-center gap-1.5 rounded-full border border-border px-4 py-2.5 text-sm"
                        >
                            <SlidersHorizontal className="h-4 w-4" />
                            Filters
                        </button>
                    </div>

                    {/* Mobile filters */}
                    <AnimatePresence>
                        {showFilters && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: "auto", opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                className="lg:hidden overflow-hidden mb-6 rounded-xl border border-border bg-white p-4"
                            >
                                <div className="flex justify-between items-center mb-3">
                                    <span className="text-sm font-bold text-navy">Filters</span>
                                    <button onClick={() => setShowFilters(false)}>
                                        <X className="h-4 w-4 text-muted" />
                                    </button>
                                </div>
                                {FiltersSidebar}
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Count */}
                    <p className="text-sm text-muted mb-4">
                        Showing{" "}
                        <span className="font-semibold text-navy">{displayed.length}</span>{" "}
                        products
                    </p>

                    {/* Grid */}
                    {loading ? (
                        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
                            {Array.from({ length: 6 }).map((_, i) => (
                                <SkeletonCard key={i} />
                            ))}
                        </div>
                    ) : displayed.length === 0 ? (
                        <div className="py-20 text-center text-muted">
                            <p className="text-lg font-medium">No products match your filters.</p>
                            <p className="mt-1 text-sm">Try adjusting your search.</p>
                        </div>
                    ) : (
                        <motion.div
                            layout
                            className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5"
                        >
                            <AnimatePresence>
                                {displayed.map((p) => (
                                    <motion.div
                                        key={p.id}
                                        layout
                                        initial={{ opacity: 0, scale: 0.95 }}
                                        animate={{ opacity: 1, scale: 1 }}
                                        exit={{ opacity: 0, scale: 0.95 }}
                                        whileHover={{
                                            y: -4,
                                            boxShadow: "0 8px 30px rgba(30,39,97,0.10)",
                                        }}
                                        className="rounded-xl border border-border bg-white p-4 flex flex-col"
                                    >
                                        <div className="h-44 rounded-lg bg-gradient-to-br from-navy/5 to-gold/10 flex items-center justify-center text-3xl select-none">
                                            {p.category === "Footwear"
                                                ? "👟"
                                                : p.category === "Accessories"
                                                    ? "👜"
                                                    : p.category === "Western Wear"
                                                        ? "👗"
                                                        : "🥻"}
                                        </div>
                                        <div className="mt-3 flex-1 space-y-1.5">
                                            <span
                                                className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${categoryColors[p.category] ?? "bg-navy/10 text-navy"
                                                    }`}
                                            >
                                                {p.category}
                                            </span>
                                            <h4 className="text-sm font-semibold text-navy line-clamp-1">
                                                {p.name}
                                            </h4>
                                            <Stars rating={p.rating ?? 4} />
                                            <p className="text-base font-bold text-navy">
                                                ₹{p.price.toLocaleString("en-IN")}
                                            </p>
                                            {p.occasionTags?.length > 0 && (
                                                <div className="flex flex-wrap gap-1">
                                                    {p.occasionTags.map((t) => (
                                                        <span
                                                            key={t}
                                                            className="rounded-full bg-navy/5 px-2 py-0.5 text-[10px] text-muted"
                                                        >
                                                            {t}
                                                        </span>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <Link
                                            href="/chat"
                                            className="mt-3 block rounded-full bg-navy py-2 text-center text-xs font-semibold text-white hover:bg-navy-light transition-colors"
                                        >
                                            Chat about this
                                        </Link>
                                    </motion.div>
                                ))}
                            </AnimatePresence>
                        </motion.div>
                    )}
                </div>
            </div>
        </div>
    );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  PAGE (wrapped in Suspense for useSearchParams)                           */
/* ═══════════════════════════════════════════════════════════════════════════ */
export default function ProductsPage() {
    return (
        <Suspense
            fallback={
                <div className="mx-auto max-w-7xl px-6 py-8">
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                        {Array.from({ length: 6 }).map((_, i) => (
                            <SkeletonCard key={i} />
                        ))}
                    </div>
                </div>
            }
        >
            <ProductsContent />
        </Suspense>
    );
}
