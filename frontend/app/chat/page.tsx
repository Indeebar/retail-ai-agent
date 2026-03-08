"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Smartphone, Monitor, MonitorSmartphone, ShoppingCart, X } from "lucide-react";
import { sendChatMessage, switchChannel, ChatResponse, Product } from "@/lib/api";

/* ── types ──────────────────────────────────────────────────────────────── */
interface Message {
    id: string;
    role: "user" | "aria";
    text: string;
    products?: Product[];
    ts: number;
}

/* ── customer picker ────────────────────────────────────────────────────── */
const DEMO_CUSTOMERS = [
    { id: "customer_001", name: "Priya Sharma" },
    { id: "customer_002", name: "Rahul Patel" },
    { id: "customer_003", name: "Ananya Iyer" },
    { id: "customer_004", name: "Vikram Singh" },
];

/* ── channel tabs ───────────────────────────────────────────────────────── */
const CHANNELS = [
    { id: "mobile", icon: Smartphone, label: "📱 Mobile" },
    { id: "web", icon: Monitor, label: "💻 Web" },
    { id: "kiosk", icon: MonitorSmartphone, label: "🖥️ Kiosk" },
];

/* ── typing indicator ───────────────────────────────────────────────────── */
function TypingIndicator() {
    return (
        <div className="flex items-center gap-2 px-4 py-3">
            <div className="flex items-center gap-1 rounded-2xl bg-white px-4 py-2.5 shadow-sm border border-border">
                <div className="typing-dot h-2 w-2 rounded-full bg-navy/50" />
                <div className="typing-dot h-2 w-2 rounded-full bg-navy/50" />
                <div className="typing-dot h-2 w-2 rounded-full bg-navy/50" />
            </div>
        </div>
    );
}

/* ── toast ───────────────────────────────────────────────────────────────── */
function Toast({ msg, onClose }: { msg: string; onClose: () => void }) {
    useEffect(() => {
        const t = setTimeout(onClose, 3000);
        return () => clearTimeout(t);
    }, [onClose]);

    return (
        <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="fixed top-20 left-1/2 z-50 -translate-x-1/2 rounded-full bg-navy px-6 py-2.5 text-sm font-medium text-white shadow-lg"
        >
            {msg}
        </motion.div>
    );
}

/* ── product card (sidebar) ─────────────────────────────────────────────── */
function SidebarProductCard({
    product,
    onAdd,
}: {
    product: Product;
    onAdd: (p: Product) => void;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl border border-border bg-white p-3 flex gap-3"
        >
            <div className="h-16 w-16 shrink-0 rounded-lg bg-gradient-to-br from-navy/5 to-gold/10 flex items-center justify-center text-xl select-none">
                {product.category === "Footwear"
                    ? "👟"
                    : product.category === "Accessories"
                        ? "👜"
                        : product.category === "Western Wear"
                            ? "👗"
                            : "🥻"}
            </div>
            <div className="flex-1 min-w-0">
                <h4 className="text-xs font-semibold text-navy truncate">
                    {product.name}
                </h4>
                <span className="inline-block mt-0.5 rounded-full bg-navy/10 px-2 py-px text-[10px] font-medium text-navy">
                    {product.category}
                </span>
                <p className="mt-1 text-sm font-bold text-navy">
                    ₹{product.price?.toLocaleString("en-IN")}
                </p>
            </div>
            <button
                onClick={() => onAdd(product)}
                className="self-end shrink-0 rounded-full bg-gold px-3 py-1 text-[10px] font-semibold text-navy hover:bg-gold-light transition-colors"
            >
                Add
            </button>
        </motion.div>
    );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  CHAT PAGE                                                                */
/* ═══════════════════════════════════════════════════════════════════════════ */
export default function ChatPage() {
    /* ── state ──────────────────────────────────────────────────────────── */
    const [messages, setMessages] = useState<Message[]>([
        {
            id: "welcome",
            role: "aria",
            text: "Hello! I'm Aria, your personal shopping assistant. What can I help you find today? 👗",
            ts: Date.now(),
        },
    ]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [sessionId, setSessionId] = useState<string | null>(null);
    const [customerId, setCustomerId] = useState("customer_001");
    const [channel, setChannel] = useState("web");

    const [recommendations, setRecommendations] = useState<Product[]>([]);
    const [cart, setCart] = useState<{ product: Product; qty: number }[]>([]);
    const [toast, setToast] = useState<string | null>(null);

    const threadRef = useRef<HTMLDivElement>(null);

    /* hydrate from localStorage on mount */
    useEffect(() => {
        if (typeof window === "undefined") return;
        const sid = localStorage.getItem("aria_session_id");
        const cid = localStorage.getItem("aria_customer_id");
        if (sid) setSessionId(sid);
        if (cid) setCustomerId(cid);
    }, []);

    /* scroll to bottom on new messages */
    useEffect(() => {
        threadRef.current?.scrollTo({
            top: threadRef.current.scrollHeight,
            behavior: "smooth",
        });
    }, [messages, loading]);

    /* ── send message ──────────────────────────────────────────────────── */
    const handleSend = useCallback(async () => {
        const text = input.trim();
        if (!text || loading) return;

        const userMsg: Message = {
            id: crypto.randomUUID(),
            role: "user",
            text,
            ts: Date.now(),
        };
        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        setLoading(true);
        setError(null);

        try {
            const res: ChatResponse = await sendChatMessage({
                message: text,
                session_id: sessionId ?? undefined,
                customer_id: customerId,
                channel,
            });

            /* persist session */
            setSessionId(res.session_id);
            localStorage.setItem("aria_session_id", res.session_id);
            localStorage.setItem("aria_customer_id", customerId);

            const ariaMsg: Message = {
                id: crypto.randomUUID(),
                role: "aria",
                text: res.reply,
                products: res.recommended_products,
                ts: Date.now(),
            };
            setMessages((prev) => [...prev, ariaMsg]);

            if (res.recommended_products?.length) {
                setRecommendations(res.recommended_products);
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Something went wrong";
            setError(msg);
        } finally {
            setLoading(false);
        }
    }, [input, loading, sessionId, customerId, channel]);

    /* ── channel switch ────────────────────────────────────────────────── */
    const handleChannelSwitch = useCallback(
        async (newChannel: string) => {
            if (newChannel === channel) return;
            setChannel(newChannel);

            if (sessionId) {
                try {
                    await switchChannel(sessionId, newChannel);
                    setToast(`Session transferred to ${newChannel} ✓`);
                } catch {
                    setToast(`Switched to ${newChannel} (offline)`);
                }
            } else {
                setToast(`Channel set to ${newChannel} ✓`);
            }
        },
        [channel, sessionId]
    );

    /* ── add to cart ───────────────────────────────────────────────────── */
    const addToCart = useCallback((p: Product) => {
        setCart((prev) => {
            const idx = prev.findIndex((c) => c.product.id === p.id);
            if (idx >= 0) {
                const next = [...prev];
                next[idx] = { ...next[idx], qty: next[idx].qty + 1 };
                return next;
            }
            return [...prev, { product: p, qty: 1 }];
        });
    }, []);

    const cartTotal = cart.reduce((s, c) => s + c.product.price * c.qty, 0);

    /* ── render ─────────────────────────────────────────────────────────── */
    return (
        <div className="mx-auto flex max-w-7xl flex-col lg:flex-row h-[calc(100vh-64px)]">
            {/* Toast */}
            <AnimatePresence>
                {toast && <Toast msg={toast} onClose={() => setToast(null)} />}
            </AnimatePresence>

            {/* ══ LEFT: Chat ═══════════════════════════════════════════════════ */}
            <div className="flex flex-col flex-[3] border-r border-border">
                {/* Header */}
                <div className="flex items-center justify-between border-b border-border px-5 py-3">
                    <div className="flex items-center gap-2">
                        <div className="relative">
                            <div className="h-9 w-9 rounded-full bg-navy flex items-center justify-center text-xs font-bold text-white">
                                A
                            </div>
                            <div className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-green-500 ring-2 ring-white" />
                        </div>
                        <div>
                            <h2 className="text-sm font-bold text-navy">Aria</h2>
                            <span className="text-[10px] text-green-600 font-medium">
                                Online
                            </span>
                        </div>
                    </div>

                    {/* Channel switcher */}
                    <div className="flex rounded-full border border-border bg-white p-0.5">
                        {CHANNELS.map((ch) => (
                            <button
                                key={ch.id}
                                onClick={() => handleChannelSwitch(ch.id)}
                                className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${channel === ch.id
                                        ? "bg-navy text-white"
                                        : "text-muted hover:text-navy"
                                    }`}
                            >
                                {ch.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Thread */}
                <div ref={threadRef} className="flex-1 overflow-y-auto p-4 space-y-3 bg-navy/[0.02]">
                    <AnimatePresence>
                        {messages.map((m) => (
                            <motion.div
                                key={m.id}
                                initial={{ opacity: 0, y: 14 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.25 }}
                                className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
                            >
                                <div
                                    className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${m.role === "user"
                                            ? "bg-navy text-white rounded-br-sm"
                                            : "bg-white text-navy shadow-sm border border-border rounded-bl-sm"
                                        }`}
                                >
                                    {m.text}
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>

                    {loading && <TypingIndicator />}

                    {error && (
                        <div className="mx-auto max-w-xs rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-xs text-red-700">
                            {error}
                        </div>
                    )}
                </div>

                {/* Input */}
                <div className="border-t border-border p-4 bg-white">
                    <div className="flex items-center gap-2">
                        {/* Customer picker */}
                        <select
                            value={customerId}
                            onChange={(e) => setCustomerId(e.target.value)}
                            className="rounded-lg border border-border bg-white px-2 py-2 text-xs text-navy focus:outline-none focus:ring-1 focus:ring-gold"
                        >
                            {DEMO_CUSTOMERS.map((c) => (
                                <option key={c.id} value={c.id}>
                                    {c.name}
                                </option>
                            ))}
                        </select>

                        <input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && handleSend()}
                            placeholder="Ask Aria anything..."
                            disabled={loading}
                            className="flex-1 rounded-full border border-border bg-white px-5 py-2.5 text-sm text-navy placeholder:text-muted focus:outline-none focus:ring-2 focus:ring-gold/40 disabled:opacity-50"
                        />

                        <button
                            onClick={handleSend}
                            disabled={loading || !input.trim()}
                            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-gold text-navy hover:bg-gold-light transition-colors disabled:opacity-40"
                        >
                            <Send className="h-4 w-4" />
                        </button>
                    </div>
                </div>
            </div>

            {/* ══ RIGHT: Product panel ═════════════════════════════════════════ */}
            <div className="hidden lg:flex flex-[2] flex-col bg-white">
                <div className="border-b border-border px-5 py-3">
                    <h3 className="text-sm font-bold text-navy">Recommended Products</h3>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {recommendations.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-center text-muted">
                            <ShoppingCart className="h-10 w-10 mb-3 text-border" />
                            <p className="text-sm">
                                Products will appear here as you chat with Aria
                            </p>
                        </div>
                    ) : (
                        recommendations.map((p) => (
                            <SidebarProductCard key={p.id} product={p} onAdd={addToCart} />
                        ))
                    )}
                </div>

                {/* Cart summary */}
                {cart.length > 0 && (
                    <div className="border-t border-border p-4 bg-navy/[0.02]">
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-xs font-semibold text-navy">
                                Cart ({cart.reduce((s, c) => s + c.qty, 0)} items)
                            </span>
                            <button
                                onClick={() => setCart([])}
                                className="text-xs text-muted hover:text-red-500 transition-colors"
                            >
                                <X className="h-3.5 w-3.5" />
                            </button>
                        </div>
                        <p className="text-lg font-bold text-navy">
                            ₹{cartTotal.toLocaleString("en-IN")}
                        </p>
                        <button className="mt-2 w-full rounded-full bg-gold py-2 text-sm font-semibold text-navy hover:bg-gold-light transition-colors">
                            Checkout
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}
