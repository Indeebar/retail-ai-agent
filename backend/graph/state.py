"""
Graph State — defines the AgentState TypedDict used by all LangGraph nodes.

Every field in AgentState is the single source of truth for the entire
conversation. Nodes read from and write partial dicts back into this state.
"""

from typing import TypedDict, Optional


class AgentState(TypedDict):
    """Full state of a conversation session flowing through the LangGraph."""

    # ── Session identity ─────────────────────────────────────────────────
    session_id: str
    customer_id: str
    channel: str  # "mobile" | "web" | "kiosk" | "whatsapp"

    # ── Conversation ─────────────────────────────────────────────────────
    messages: list[dict]  # Each: {"role": "user"|"assistant", "content": "..."}
    current_message: str  # The latest user message
    intent: str  # Detected intent of current message

    # ── Shopping state ───────────────────────────────────────────────────
    cart: list[dict]  # Each: {"sku_id": "...", "name": "...", "price": N, "quantity": 1}
    current_order_id: Optional[str]

    # ── Agent outputs (populated by worker agents) ───────────────────────
    recommendation_result: Optional[dict]
    inventory_result: Optional[dict]
    loyalty_result: Optional[dict]
    payment_result: Optional[dict]
    fulfillment_result: Optional[dict]
    post_purchase_result: Optional[dict]

    # ── Final response ───────────────────────────────────────────────────
    final_response: str  # What gets sent back to the user

    # ── Tracking ─────────────────────────────────────────────────────────
    payment_status: str  # "none" | "pending" | "success" | "failed"
    fulfillment_status: str  # "none" | "scheduled" | "confirmed"
    error: Optional[str]


def create_initial_state(
    session_id: str, customer_id: str, channel: str
) -> AgentState:
    """
    Return an AgentState with all fields set to their default empty values.

    Args:
        session_id:   Unique session identifier.
        customer_id:  Customer profile ID (e.g. "customer_001").
        channel:      Interaction channel ("web", "mobile", "kiosk", "whatsapp").

    Returns:
        A fully-initialised AgentState dict.
    """
    return AgentState(
        session_id=session_id,
        customer_id=customer_id,
        channel=channel,
        messages=[],
        current_message="",
        intent="",
        cart=[],
        current_order_id=None,
        recommendation_result=None,
        inventory_result=None,
        loyalty_result=None,
        payment_result=None,
        fulfillment_result=None,
        post_purchase_result=None,
        final_response="",
        payment_status="none",
        fulfillment_status="none",
        error=None,
    )
