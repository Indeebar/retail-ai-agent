"""
Fulfillment Agent — schedules delivery or in-store pickup after payment.

Calls the fulfillment mock API to create a delivery/pickup order and
builds a confirmation message based on fulfillment type.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

import httpx

logger = logging.getLogger(__name__)

BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")


async def run(input: dict) -> dict:
    """
    Schedule delivery or in-store pickup after payment success.

    Input dict fields:
        order_id: str
        fulfillment_type: str — "SHIP_HOME" | "CLICK_COLLECT" | "IN_STORE"
        customer_id: str
        sku_ids: list[str]

    Returns dict with tracking_id, fulfillment_type, confirmation_message, details, agent.
    """
    order_id: str = input.get("order_id", "")
    fulfillment_type: str = input.get("fulfillment_type", "SHIP_HOME")
    customer_id: str = input.get("customer_id", "")
    sku_ids: list = input.get("sku_ids", [])

    try:
        async with httpx.AsyncClient(base_url=BACKEND_API_URL, timeout=30.0) as client:
            payload = {
                "order_id": order_id,
                "fulfillment_type": fulfillment_type,
                "customer_id": customer_id,
                "sku_ids": sku_ids,
            }

            response = await client.post("/fulfillment", json=payload)
            response.raise_for_status()
            data = response.json()

        logger.info("Fulfillment created: order=%s type=%s tracking=%s", order_id, fulfillment_type, data.get("tracking_id"))

        tracking_id = data.get("tracking_id", "N/A")

        # Build confirmation message based on type
        if fulfillment_type == "SHIP_HOME":
            estimated = data.get("estimated_delivery", "3-5 business days")
            confirmation = f"📦 Order confirmed! Your items will be delivered by {estimated}. Tracking ID: {tracking_id}"
        elif fulfillment_type == "CLICK_COLLECT":
            slot = data.get("pickup_slot", "Tomorrow")
            confirmation = f"🏪 Order ready for pickup! Slot: {slot}. Tracking ID: {tracking_id}"
        elif fulfillment_type == "IN_STORE":
            confirmation = f"✅ Items reserved at your nearest store for 24 hours. Tracking ID: {tracking_id}"
        else:
            confirmation = f"📋 Fulfillment created. Tracking ID: {tracking_id}"

        return {
            "tracking_id": tracking_id,
            "fulfillment_type": fulfillment_type,
            "confirmation_message": confirmation,
            "details": data,
            "agent": "fulfillment",
        }

    except httpx.HTTPStatusError as e:
        logger.error("Fulfillment API HTTP error: %s — %s", e.response.status_code, e.response.text)
        return {
            "tracking_id": None,
            "fulfillment_type": fulfillment_type,
            "confirmation_message": f"❌ Could not schedule fulfillment. Error: {e.response.status_code}",
            "details": {},
            "agent": "fulfillment",
        }
    except Exception as e:
        logger.error("Fulfillment scheduling failed: %r", e)
        return {
            "tracking_id": None,
            "fulfillment_type": fulfillment_type,
            "confirmation_message": "❌ Could not schedule fulfillment. Please try again.",
            "details": {},
            "agent": "fulfillment",
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    test_input = {
        "order_id": "ORD_TEST_001",
        "fulfillment_type": "SHIP_HOME",
        "customer_id": "customer_001",
        "sku_ids": ["SKU_001"],
    }

    print("\n" + "=" * 60)
    print("FULFILLMENT AGENT TEST")
    print("=" * 60)
    print(f"Order: {test_input['order_id']}")
    print(f"Type: {test_input['fulfillment_type']}")
    print(f"Customer: {test_input['customer_id']}")
    print(f"SKUs: {test_input['sku_ids']}")
    print("-" * 60)

    result = asyncio.run(run(test_input))

    print(f"\n✅ Agent: {result['agent']}")
    print(f"🔗 Tracking ID: {result['tracking_id']}")
    print(f"📦 Type: {result['fulfillment_type']}")
    print(f"💬 Confirmation:\n{result['confirmation_message']}")
    print(f"\n📊 Details:")
    for key, val in result.get("details", {}).items():
        print(f"   {key}: {val}")

    print("\n" + "=" * 60)
    print("✅ Fulfillment agent test PASSED")
    print("=" * 60)
