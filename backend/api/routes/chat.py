"""
Chat Route — POST /chat and POST /chat/switch-channel endpoints.

The main conversational interface. Manages session lifecycle via Redis
and delegates to the LangGraph agent graph for processing.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from graph.agent_graph import run_graph
from session import session_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════

class ChatRequest(BaseModel):
    """Incoming chat message from any channel."""
    message: str
    session_id: Optional[str] = None  # None = create a new session
    customer_id: str
    channel: str = "web"


class ChatResponse(BaseModel):
    """Response sent back to the client after graph execution."""
    reply: str
    session_id: str
    recommended_products: list = []
    cart: list = []
    payment_status: str = "none"
    fulfillment_status: str = "none"
    intent: str = ""


class ChannelSwitchRequest(BaseModel):
    """Request to switch a session's channel."""
    session_id: str
    new_channel: str


class ChannelSwitchResponse(BaseModel):
    """Response after switching channels."""
    session_id: str
    old_channel: str
    new_channel: str
    message: str


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """
    POST /chat — Main conversational endpoint.

    1. If session_id is None → create a new session
    2. Load existing session state from Redis
    3. Run the LangGraph agent graph
    4. Save updated state back to Redis
    5. Return the response
    """
    logger.info("POST /chat — message=%r session=%s customer=%s channel=%s",
                req.message[:60], req.session_id, req.customer_id, req.channel)

    # 1. Create or load session
    if req.session_id is None:
        session_id = await session_manager.create_session(req.customer_id, req.channel)
        existing_state = None
        logger.info("New session created: %s", session_id)
    else:
        session_id = req.session_id
        existing_state = await session_manager.get_session(session_id)
        if existing_state is None:
            # Session expired or not found — create a new one
            session_id = await session_manager.create_session(req.customer_id, req.channel)
            existing_state = None
            logger.info("Session expired, created new: %s", session_id)

    # 2. Run the agent graph
    try:
        final_state = await run_graph(
            message=req.message,
            session_id=session_id,
            customer_id=req.customer_id,
            channel=req.channel,
            existing_state=existing_state,
        )
    except Exception as e:
        logger.error("Graph execution failed: %r", e)
        raise HTTPException(status_code=500, detail=f"Agent graph error: {str(e)}")

    # 3. Save updated state back to Redis
    await session_manager.save_session(session_id, final_state)

    # 4. Extract recommended products from result
    rec_result = final_state.get("recommendation_result")
    recommended_products = rec_result.get("recommended_products", []) if rec_result else []

    # 5. Build response
    response = ChatResponse(
        reply=final_state.get("final_response", ""),
        session_id=session_id,
        recommended_products=recommended_products,
        cart=final_state.get("cart", []),
        payment_status=final_state.get("payment_status", "none"),
        fulfillment_status=final_state.get("fulfillment_status", "none"),
        intent=final_state.get("intent", ""),
    )

    logger.info("POST /chat — response sent (intent=%s, reply_len=%d)",
                response.intent, len(response.reply))
    return response


@router.post("/switch-channel", response_model=ChannelSwitchResponse)
async def switch_channel(req: ChannelSwitchRequest):
    """
    POST /chat/switch-channel — Switch the channel for an existing session.

    This preserves the entire conversation history while changing
    the interaction channel (e.g. web → mobile).
    """
    logger.info("POST /chat/switch-channel — session=%s new_channel=%s",
                req.session_id, req.new_channel)

    # Load existing session to get old channel
    existing = await session_manager.get_session(req.session_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Session {req.session_id} not found")

    old_channel = existing.get("channel", "unknown")

    updated = await session_manager.switch_channel(req.session_id, req.new_channel)
    if updated is None:
        raise HTTPException(status_code=500, detail="Failed to switch channel")

    return ChannelSwitchResponse(
        session_id=req.session_id,
        old_channel=old_channel,
        new_channel=req.new_channel,
        message=f"Session switched from {old_channel} to {req.new_channel}",
    )
