"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
    CheckCircle2,
    Circle,
    Package,
    ChevronDown,
    ChevronUp,
    RotateCcw,
} from "lucide-react";

/* ── types ──────────────────────────────────────────────────────────────── */
interface OrderItem {
    name: string;
    qty: number;
    price: number;
    emoji: string;
}

interface Order {
    id: string;
    date: string;
    items: OrderItem[];
    total: number;
    savings: number;
    currentStep: number;
}

/* ── timeline steps ─────────────────────────────────────────────────────── */
const STEPS = [
    "Order Placed",
    "Packed",
    "Dispatched",
    "In Transit",
    "Out for Delivery",
    "Delivered",
];

/* ── demo orders ────────────────────────────────────────────────────────── */
const DEMO_ORDERS: Order[] = [
    {
        id: "ORD-2026-001847",
        date: "March 5, 2026",
        items: [
            { name: "Banarasi Silk Saree", qty: 1, price: 8999, emoji: "🥻" },
            { name: "Gold Temple Jhumkas", qty: 1, price: 2499, emoji: "👜" },
        ],
        total: 10348,
        savings: 1150,
        currentStep: 3,
    },
    {
        id: "ORD-2026-001692",
        date: "February 28, 2026",
        items: [
            { name: "Embroidered Anarkali Set", qty: 1, price: 5499, emoji: "🥻" },
            { name: "Block Print Palazzo Pants", qty: 2, price: 1899, emoji: "👗" },
        ],
        total: 8397,
        savings: 900,
        currentStep: 5,
    },
];

/* ── timeline component ─────────────────────────────────────────────────── */
function OrderTimeline({ currentStep }: { currentStep: number }) {
    return (
        <div className="py-4">
            <div className="relative flex items-start justify-between">
                {/* Line behind dots */}
                <div className="absolute top-3 left-3 right-3 h-0.5 bg-border" />
                <div
                    className="absolute top-3 left-3 h-0.5 bg-navy transition-all duration-700"
                    style={{
                        width: `calc(${(Math.min(currentStep, STEPS.length - 1) / (STEPS.length - 1)) * 100}% - 24px)`,
                    }}
                />

                {STEPS.map((step, i) => {
                    const isComplete = i < currentStep;
                    const isActive = i === currentStep;
                    const isPending = i > currentStep;

                    return (
                        <div
                            key={step}
                            className="relative z-10 flex flex-col items-center"
                            style={{ width: `${100 / STEPS.length}%` }}
                        >
                            {/* Dot */}
                            {isComplete ? (
                                <CheckCircle2 className="h-6 w-6 text-green-600 bg-white rounded-full" />
                            ) : isActive ? (
                                <div className="timeline-pulse h-6 w-6 rounded-full bg-gold border-2 border-white" />
                            ) : (
                                <Circle className="h-6 w-6 text-border bg-white rounded-full" />
                            )}
                            {/* Label */}
                            <span
                                className={`mt-2 text-[10px] font-medium text-center leading-tight ${isComplete
                                        ? "text-navy"
                                        : isActive
                                            ? "text-gold font-bold"
                                            : "text-muted"
                                    }`}
                            >
                                {step}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

/* ── order card ─────────────────────────────────────────────────────────── */
function OrderCard({ order, index }: { order: Order; index: number }) {
    const [expanded, setExpanded] = useState(false);

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.15, duration: 0.4 }}
            className="rounded-xl border border-border bg-white shadow-sm overflow-hidden"
        >
            {/* Header */}
            <div className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-full bg-navy/5 flex items-center justify-center">
                        <Package className="h-5 w-5 text-navy" />
                    </div>
                    <div>
                        <p className="text-sm font-bold text-navy">{order.id}</p>
                        <p className="text-xs text-muted">{order.date}</p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    <div className="text-right">
                        <p className="text-base font-bold text-navy">
                            ₹{order.total.toLocaleString("en-IN")}
                        </p>
                        <p className="text-xs text-green-600 font-medium">
                            Saved ₹{order.savings.toLocaleString("en-IN")}
                        </p>
                    </div>
                    <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${order.currentStep >= STEPS.length - 1
                                ? "bg-green-100 text-green-700"
                                : "bg-gold/15 text-navy"
                            }`}
                    >
                        {STEPS[Math.min(order.currentStep, STEPS.length - 1)]}
                    </span>
                </div>
            </div>

            {/* Items */}
            <div className="px-5 pb-2 flex flex-wrap gap-3">
                {order.items.map((item) => (
                    <div
                        key={item.name}
                        className="flex items-center gap-2 rounded-lg bg-navy/[0.03] px-3 py-2"
                    >
                        <span className="text-lg">{item.emoji}</span>
                        <div>
                            <p className="text-xs font-semibold text-navy">{item.name}</p>
                            <p className="text-[10px] text-muted">
                                Qty: {item.qty} · ₹{item.price.toLocaleString("en-IN")}
                            </p>
                        </div>
                    </div>
                ))}
            </div>

            {/* Actions */}
            <div className="px-5 py-3 flex gap-3 border-t border-border/50">
                <button
                    onClick={() => setExpanded(!expanded)}
                    className="flex items-center gap-1 rounded-full bg-navy px-4 py-1.5 text-xs font-semibold text-white hover:bg-navy-light transition-colors"
                >
                    {expanded ? (
                        <>
                            Hide Timeline <ChevronUp className="h-3 w-3" />
                        </>
                    ) : (
                        <>
                            Track Order <ChevronDown className="h-3 w-3" />
                        </>
                    )}
                </button>
                <button className="flex items-center gap-1 rounded-full border border-border px-4 py-1.5 text-xs font-semibold text-navy hover:bg-navy/5 transition-colors">
                    <RotateCcw className="h-3 w-3" />
                    Return Item
                </button>
            </div>

            {/* Expanded timeline */}
            {expanded && (
                <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="px-5 pb-5 pt-1"
                >
                    <OrderTimeline currentStep={order.currentStep} />
                </motion.div>
            )}
        </motion.div>
    );
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/*  PAGE                                                                     */
/* ═══════════════════════════════════════════════════════════════════════════ */
export default function OrdersPage() {
    return (
        <div className="mx-auto max-w-3xl px-6 py-10">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-navy">Your Orders</h1>
                <p className="mt-1 text-sm text-muted">
                    Track your orders and manage returns
                </p>
            </div>

            <div className="space-y-5">
                {DEMO_ORDERS.map((order, i) => (
                    <OrderCard key={order.id} order={order} index={i} />
                ))}
            </div>
        </div>
    );
}
