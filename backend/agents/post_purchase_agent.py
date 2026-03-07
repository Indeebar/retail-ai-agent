"""
Post-Purchase Agent — handles tracking, returns, and feedback.

All post-purchase interactions are simulated since there is no real
order database. Supports TRACK, RETURN, and FEEDBACK actions.
"""

import asyncio
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


async def run(input: dict) -> dict:
    """
    Handle post-purchase interactions — tracking, returns, feedback.

    Input dict fields:
        action: str — "TRACK" | "RETURN" | "FEEDBACK"
        order_id: str
        customer_id: str
        feedback_text: str (only for FEEDBACK action)

    Returns dict with action, order_id, response, data, agent.
    """
    action: str = input.get("action", "TRACK").upper()
    order_id: str = input.get("order_id", "")
    customer_id: str = input.get("customer_id", "")
    feedback_text: str = input.get("feedback_text", "")

    try:
        if action == "TRACK":
            return await _handle_track(order_id, customer_id)
        elif action == "RETURN":
            return await _handle_return(order_id, customer_id)
        elif action == "FEEDBACK":
            return await _handle_feedback(order_id, customer_id, feedback_text)
        else:
            logger.warning("Unknown post-purchase action: %s", action)
            return {
                "action": action,
                "order_id": order_id,
                "response": f"⚠️ Unknown action '{action}'. Supported actions: TRACK, RETURN, FEEDBACK.",
                "data": {},
                "agent": "post_purchase",
            }
    except Exception as e:
        logger.error("Post-purchase action %s failed: %r", action, e)
        return {
            "action": action,
            "order_id": order_id,
            "response": "❌ Something went wrong. Please try again.",
            "data": {},
            "agent": "post_purchase",
        }


async def _handle_track(order_id: str, customer_id: str) -> dict:
    """Generate a realistic mock tracking timeline."""
    logger.info("Tracking order %s for customer %s", order_id, customer_id)

    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    timeline = [
        {"status": "Order Placed", "emoji": "✅", "timestamp": "2 days ago"},
        {"status": "Packed", "emoji": "✅", "timestamp": "1 day ago"},
        {"status": "Dispatched", "emoji": "✅", "timestamp": "1 day ago"},
        {"status": "In Transit", "emoji": "🚚", "timestamp": "Today"},
        {"status": "Out for Delivery", "emoji": "⏳", "timestamp": f"Expected {tomorrow}"},
    ]

    timeline_str = " → ".join([f"{s['emoji']} {s['status']}" for s in timeline])
    response = (
        f"📦 Order {order_id} — Tracking Update\n\n"
        f"{timeline_str}\n\n"
        f"📍 Current Status: In Transit\n"
        f"📅 Estimated Delivery: {tomorrow}\n"
        f"🚚 Carrier: BlueDart Express"
    )

    return {
        "action": "TRACK",
        "order_id": order_id,
        "response": response,
        "data": {
            "current_status": "In Transit",
            "estimated_delivery": tomorrow,
            "carrier": "BlueDart Express",
            "timeline": timeline,
        },
        "agent": "post_purchase",
    }


async def _handle_return(order_id: str, customer_id: str) -> dict:
    """Return a return initiation response with pickup details."""
    logger.info("Initiating return for order %s, customer %s", order_id, customer_id)

    pickup_date = (date.today() + timedelta(days=3)).isoformat()
    return_id = f"RET_{order_id.replace('ORD_', '')}"

    response = (
        f"🔄 Return Initiated for Order {order_id}\n\n"
        f"📋 Return ID: {return_id}\n"
        f"📅 Pickup Scheduled: {pickup_date}\n"
        f"💰 Refund Timeline: 5-7 business days after pickup\n"
        f"📦 Please keep the item in its original packaging.\n\n"
        f"Our delivery partner will contact you to confirm the pickup slot."
    )

    return {
        "action": "RETURN",
        "order_id": order_id,
        "response": response,
        "data": {
            "return_id": return_id,
            "pickup_date": pickup_date,
            "refund_timeline": "5-7 business days",
            "status": "initiated",
        },
        "agent": "post_purchase",
    }


async def _handle_feedback(order_id: str, customer_id: str, feedback_text: str) -> dict:
    """Acknowledge the feedback warmly."""
    logger.info("Feedback received for order %s from %s: %s", order_id, customer_id, feedback_text[:50])

    response = (
        f"🙏 Thank you for your feedback on Order {order_id}!\n\n"
        f"We truly appreciate you taking the time to share your thoughts. "
        f"Your feedback helps us improve and serve you better.\n\n"
        f"If you need any further help, I'm always here for you! 💛"
    )

    return {
        "action": "FEEDBACK",
        "order_id": order_id,
        "response": response,
        "data": {
            "feedback_text": feedback_text,
            "status": "received",
            "acknowledged": True,
        },
        "agent": "post_purchase",
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    # Test all 3 actions
    tests = [
        {
            "name": "TRACK",
            "input": {"action": "TRACK", "order_id": "ORD_TEST_001", "customer_id": "customer_001"},
        },
        {
            "name": "RETURN",
            "input": {"action": "RETURN", "order_id": "ORD_TEST_001", "customer_id": "customer_001"},
        },
        {
            "name": "FEEDBACK",
            "input": {
                "action": "FEEDBACK",
                "order_id": "ORD_TEST_001",
                "customer_id": "customer_001",
                "feedback_text": "Great quality saree, loved the fabric and color!",
            },
        },
    ]

    for test in tests:
        print("\n" + "=" * 60)
        print(f"POST-PURCHASE AGENT TEST — {test['name']}")
        print("=" * 60)

        result = asyncio.run(run(test["input"]))

        print(f"\n✅ Agent: {result['agent']}")
        print(f"📋 Action: {result['action']}")
        print(f"📦 Order: {result['order_id']}")
        print(f"\n💬 Response:\n{result['response']}")
        print(f"\n📊 Data: {result['data']}")

    print("\n" + "=" * 60)
    print("✅ All post-purchase agent tests PASSED")
    print("=" * 60)
