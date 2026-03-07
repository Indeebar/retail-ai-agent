"""
Agent Graph — LangGraph StateGraph wiring all 9 nodes for the retail AI agent.

This is the core orchestration layer. Every user message enters at
intent_detection, gets routed to the appropriate worker node(s), and
exits with a final_response in the AgentState.

Uses LangGraph 0.2.x API only:
  - from langgraph.graph import StateGraph, END
  - StateGraph takes the AgentState TypedDict directly as schema
  - add_node(), add_edge(), add_conditional_edges(), .compile()
"""

import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path

# ── Ensure backend/ is on sys.path ──────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import StateGraph, END

from graph.state import AgentState, create_initial_state
from agents import (
    sales_agent,
    recommendation_agent,
    inventory_agent,
    loyalty_agent,
    payment_agent,
    fulfillment_agent,
    post_purchase_agent,
)

from groq import Groq

logger = logging.getLogger(__name__)

# ── Data helpers ────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_customers() -> list[dict]:
    """Load all customer profiles from customers.json."""
    with open(DATA_DIR / "customers.json", "r", encoding="utf-8") as f:
        return json.load(f)


def _find_customer(customer_id: str) -> dict | None:
    """Find a single customer by ID."""
    for c in _load_customers():
        if c["id"] == customer_id:
            return c
    return None


# ═══════════════════════════════════════════════════════════════════════════
# NODE FUNCTIONS  (each is async, takes AgentState, returns partial dict)
# ═══════════════════════════════════════════════════════════════════════════


# ── 1. Intent Detection ─────────────────────────────────────────────────────

async def intent_detection_node(state: AgentState) -> dict:
    """Detect customer intent using the sales agent."""
    logger.info("──▸ [intent_detection_node] ENTER  message=%r", state["current_message"][:80])
    detected = await sales_agent.detect_intent(
        state["current_message"], state["messages"]
    )
    logger.info("──▸ [intent_detection_node] EXIT   intent=%s", detected)
    return {"intent": detected}


# ── 2. Recommendation ───────────────────────────────────────────────────────

async def recommendation_node(state: AgentState) -> dict:
    """Generate product recommendations via RAG + Groq."""
    logger.info("──▸ [recommendation_node] ENTER  customer=%s query=%r", state["customer_id"], state["current_message"][:60])

    result = await recommendation_agent.run({
        "customer_id": state["customer_id"],
        "query": state["current_message"],
        "conversation_history": state["messages"],
        "cart": state["cart"],
    })

    llm_response = result.get("llm_response", "Here are some recommendations for you!")
    updated_messages = list(state["messages"]) + [
        {"role": "assistant", "content": llm_response}
    ]

    logger.info("──▸ [recommendation_node] EXIT   products=%d response_len=%d",
                len(result.get("recommended_products", [])), len(llm_response))
    return {
        "recommendation_result": result,
        "messages": updated_messages,
        "final_response": llm_response,
    }


# ── 3. Inventory ────────────────────────────────────────────────────────────

async def inventory_node(state: AgentState) -> dict:
    """Check stock availability for a SKU."""
    logger.info("──▸ [inventory_node] ENTER  message=%r", state["current_message"][:80])

    # Extract SKU from message  (e.g. "SKU_001")
    sku_match = re.search(r"SKU_\d+", state["current_message"], re.IGNORECASE)
    sku_id = sku_match.group(0).upper() if sku_match else ""

    # Extract city — try from message, fall back to customer profile
    customer = _find_customer(state["customer_id"])
    customer_city = customer.get("city", "") if customer else ""

    result = await inventory_agent.run({
        "sku_id": sku_id,
        "customer_city": customer_city,
    })

    message_text = result.get("message", "I couldn't check availability right now.")
    updated_messages = list(state["messages"]) + [
        {"role": "assistant", "content": message_text}
    ]

    logger.info("──▸ [inventory_node] EXIT   sku=%s available=%s", sku_id, result.get("is_available"))
    return {
        "inventory_result": result,
        "messages": updated_messages,
        "final_response": message_text,
    }


# ── 4. Loyalty ──────────────────────────────────────────────────────────────

async def loyalty_node(state: AgentState) -> dict:
    """Apply loyalty perks and calculate final pricing (feeds into payment)."""
    logger.info("──▸ [loyalty_node] ENTER  customer=%s cart_items=%d", state["customer_id"], len(state["cart"]))

    result = await loyalty_agent.run({
        "customer_id": state["customer_id"],
        "cart": state["cart"],
    })

    logger.info("──▸ [loyalty_node] EXIT   original=%.0f final=%.0f savings=%.0f",
                result.get("original_total", 0), result.get("final_total", 0), result.get("total_savings", 0))
    # NOTE: loyalty_node does NOT set final_response — it feeds into payment_node
    return {"loyalty_result": result}


# ── 5. Payment ──────────────────────────────────────────────────────────────

async def payment_node(state: AgentState) -> dict:
    """Process payment with retry logic."""
    logger.info("──▸ [payment_node] ENTER  session=%s", state["session_id"])

    order_id = "ORD_" + state["session_id"][-6:]

    # Get amount from loyalty result if available, else sum cart prices
    loyalty = state.get("loyalty_result")
    if loyalty and loyalty.get("final_total"):
        amount = loyalty["final_total"]
    else:
        amount = sum(item.get("price", 0) * item.get("quantity", 1) for item in state["cart"])

    # Get payment method from customer profile
    customer = _find_customer(state["customer_id"])
    method = "upi"
    if customer:
        saved = customer.get("savedPaymentMethods", [])
        if saved:
            method = saved[0]

    result = await payment_agent.run({
        "order_id": order_id,
        "method": method,
        "amount": amount,
        "customer_id": state["customer_id"],
    })

    payment_status = "success" if result.get("success") else "failed"

    logger.info("──▸ [payment_node] EXIT   order=%s status=%s amount=%.0f", order_id, payment_status, amount)
    return {
        "payment_result": result,
        "current_order_id": order_id,
        "payment_status": payment_status,
        "final_response": result.get("message", "Payment processed."),
    }


# ── 6. Fulfillment ─────────────────────────────────────────────────────────

async def fulfillment_node(state: AgentState) -> dict:
    """Schedule delivery/pickup after successful payment."""
    logger.info("──▸ [fulfillment_node] ENTER  order=%s payment_status=%s",
                state.get("current_order_id"), state.get("payment_status"))

    # Only run if payment was successful
    if state.get("payment_status") != "success":
        logger.info("──▸ [fulfillment_node] SKIP — payment not successful")
        return {
            "fulfillment_result": {"skipped": True},
            "fulfillment_status": "none",
            "final_response": state.get("final_response", ""),
        }

    sku_ids = [item.get("sku_id", "") for item in state["cart"]]

    result = await fulfillment_agent.run({
        "order_id": state["current_order_id"],
        "fulfillment_type": "SHIP_HOME",
        "customer_id": state["customer_id"],
        "sku_ids": sku_ids,
    })

    confirmation = result.get("confirmation_message", "Fulfillment scheduled.")

    logger.info("──▸ [fulfillment_node] EXIT   tracking=%s", result.get("tracking_id"))
    return {
        "fulfillment_result": result,
        "fulfillment_status": "confirmed",
        "final_response": confirmation,
    }


# ── 7. Post-Purchase ───────────────────────────────────────────────────────

async def post_purchase_node(state: AgentState) -> dict:
    """Handle tracking, returns, or feedback."""
    logger.info("──▸ [post_purchase_node] ENTER  intent=%s message=%r", state["intent"], state["current_message"][:60])

    # Map intent to action
    action_map = {"TRACK": "TRACK", "RETURN": "RETURN", "FEEDBACK": "FEEDBACK"}
    action = action_map.get(state["intent"], "TRACK")

    result = await post_purchase_agent.run({
        "action": action,
        "order_id": state.get("current_order_id", "ORD_UNKNOWN"),
        "customer_id": state["customer_id"],
        "feedback_text": state["current_message"] if action == "FEEDBACK" else "",
    })

    response_text = result.get("response", "I'll look into that for you.")
    updated_messages = list(state["messages"]) + [
        {"role": "assistant", "content": response_text}
    ]

    logger.info("──▸ [post_purchase_node] EXIT   action=%s", action)
    return {
        "post_purchase_result": result,
        "messages": updated_messages,
        "final_response": response_text,
    }


# ── 8. Greeting ─────────────────────────────────────────────────────────────

async def greeting_node(state: AgentState) -> dict:
    """Generate a warm, personalised greeting using Groq."""
    logger.info("──▸ [greeting_node] ENTER  customer=%s", state["customer_id"])

    customer = _find_customer(state["customer_id"])
    name = customer.get("name", "there") if customer else "there"
    tier = customer.get("loyaltyTier", "Valued") if customer else "Valued"

    try:
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"You are Aria, a warm premium fashion sales associate. "
                        f"Greet {name}, a {tier} loyalty member, in 1-2 sentences. "
                        f"Be personal and enthusiastic. Mention their loyalty tier."
                    ),
                },
                {"role": "user", "content": state["current_message"]},
            ],
            temperature=0.7,
            max_tokens=100,
        )
        greeting = completion.choices[0].message.content
    except Exception as e:
        logger.error("Greeting generation failed: %r", e)
        greeting = f"Hello {name}! Welcome back — great to see our {tier} member. How can I help you today?"

    updated_messages = list(state["messages"]) + [
        {"role": "assistant", "content": greeting}
    ]

    logger.info("──▸ [greeting_node] EXIT   response_len=%d", len(greeting))
    return {
        "messages": updated_messages,
        "final_response": greeting,
    }


# ── 9. Fallback ─────────────────────────────────────────────────────────────

async def fallback_node(state: AgentState) -> dict:
    """Handle unclear intents with a helpful prompt."""
    logger.info("──▸ [fallback_node] ENTER  message=%r", state["current_message"][:60])

    fallback_text = (
        "I'd love to help! Are you looking for product recommendations, "
        "checking availability, or something else?"
    )

    updated_messages = list(state["messages"]) + [
        {"role": "assistant", "content": fallback_text}
    ]

    logger.info("──▸ [fallback_node] EXIT")
    return {
        "messages": updated_messages,
        "final_response": fallback_text,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ROUTING
# ═══════════════════════════════════════════════════════════════════════════

def route_by_intent(state: AgentState) -> str:
    """Route to the appropriate node based on detected intent."""
    intent_to_node = {
        "RECOMMEND": "recommendation_node",
        "INVENTORY": "inventory_node",
        "CHECKOUT": "loyalty_node",
        "TRACK": "post_purchase_node",
        "RETURN": "post_purchase_node",
        "FEEDBACK": "post_purchase_node",
        "GREETING": "greeting_node",
        "UNCLEAR": "fallback_node",
    }
    target = intent_to_node.get(state["intent"], "fallback_node")
    logger.info("──▸ [route_by_intent] intent=%s → %s", state["intent"], target)
    return target


# ═══════════════════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ═══════════════════════════════════════════════════════════════════════════

def build_graph():
    """Build and compile the LangGraph StateGraph with all 9 nodes."""
    logger.info("Building LangGraph StateGraph …")

    graph = StateGraph(AgentState)

    # Add all 9 nodes
    graph.add_node("intent_detection", intent_detection_node)
    graph.add_node("recommendation_node", recommendation_node)
    graph.add_node("inventory_node", inventory_node)
    graph.add_node("loyalty_node", loyalty_node)
    graph.add_node("payment_node", payment_node)
    graph.add_node("fulfillment_node", fulfillment_node)
    graph.add_node("post_purchase_node", post_purchase_node)
    graph.add_node("greeting_node", greeting_node)
    graph.add_node("fallback_node", fallback_node)

    # Entry point
    graph.set_entry_point("intent_detection")

    # Conditional routing after intent detection
    graph.add_conditional_edges("intent_detection", route_by_intent)

    # Checkout chain: loyalty → payment → fulfillment → END
    graph.add_edge("loyalty_node", "payment_node")
    graph.add_edge("payment_node", "fulfillment_node")

    # All other nodes go straight to END
    for node in [
        "recommendation_node",
        "inventory_node",
        "fulfillment_node",
        "post_purchase_node",
        "greeting_node",
        "fallback_node",
    ]:
        graph.add_edge(node, END)

    compiled = graph.compile()
    logger.info("LangGraph compiled successfully — 9 nodes, 1 conditional edge")
    return compiled


# ── Singleton compiled graph ─────────────────────────────────────────────
_compiled_graph = None


def _get_graph():
    """Return the compiled graph (singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

async def run_graph(
    message: str,
    session_id: str,
    customer_id: str,
    channel: str,
    existing_state: dict = None,
) -> dict:
    """
    Run the full agent graph for a single user message.

    Args:
        message:        The user's current message.
        session_id:     Unique session ID.
        customer_id:    Customer profile ID.
        channel:        Interaction channel.
        existing_state: Optional previous state dict to continue from.

    Returns:
        The final AgentState dict after graph execution.
    """
    logger.info("═══ run_graph START  session=%s customer=%s channel=%s", session_id, customer_id, channel)
    logger.info("═══ User message: %r", message)

    if existing_state:
        state = dict(existing_state)
        state["current_message"] = message
        # Append user message to conversation history
        state["messages"] = list(state.get("messages", [])) + [
            {"role": "user", "content": message}
        ]
    else:
        state = create_initial_state(session_id, customer_id, channel)
        state["current_message"] = message
        state["messages"] = [{"role": "user", "content": message}]

    compiled = _get_graph()
    final_state = await compiled.ainvoke(state)

    logger.info("═══ run_graph END    intent=%s response_len=%d",
                final_state.get("intent"), len(final_state.get("final_response", "")))
    return dict(final_state)


# ═══════════════════════════════════════════════════════════════════════════
# __main__ — 3-turn conversation test
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Fix Windows cp1252 encoding errors with emoji chars
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    async def test_conversation():
        session_id = "test_session_001"
        customer_id = "customer_001"
        channel = "web"

        turns = [
            ("Turn 1", "Hi there, I'm looking for a wedding outfit"),
            ("Turn 2", "Is SKU_001 available in Mumbai?"),
            ("Turn 3", "I want to buy it"),
        ]

        state = None

        for label, message in turns:
            print(f"\n{'=' * 70}")
            print(f"  {label} — User: {message}")
            print(f"{'=' * 70}")

            state = await run_graph(
                message=message,
                session_id=session_id,
                customer_id=customer_id,
                channel=channel,
                existing_state=state,
            )

            print(f"\n  Intent: {state.get('intent')}")
            print(f"  Aria: {state.get('final_response', '(no response)')}")
            print(f"  Messages in history: {len(state.get('messages', []))}")
            print(f"  Cart items: {len(state.get('cart', []))}")
            print(f"  Payment status: {state.get('payment_status')}")
            print(f"  Fulfillment status: {state.get('fulfillment_status')}")

        print(f"\n{'=' * 70}")
        print("✅ 3-turn conversation test complete")
        print(f"{'=' * 70}")

    asyncio.run(test_conversation())
