"""
Inventory Agent — checks real-time stock availability via the mock API.

Calls the inventory endpoint to get stock levels and fulfillment options
for a given SKU, then builds a human-readable availability message.
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
    Check inventory availability for a specific SKU.

    Input dict fields:
        sku_id: str
        customer_city: str
        preferred_fulfillment: str (optional, default "SHIP_HOME")

    Returns dict with sku_id, availability, fulfillment_options, message, is_available, agent.
    """
    sku_id: str = input.get("sku_id", "")
    customer_city: str = input.get("customer_city", "")
    preferred_fulfillment: str = input.get("preferred_fulfillment", "SHIP_HOME")

    try:
        async with httpx.AsyncClient(base_url=BACKEND_API_URL, timeout=10.0) as client:
            params = {}
            if customer_city:
                params["customer_city"] = customer_city

            response = await client.get(f"/inventory/{sku_id}", params=params)
            response.raise_for_status()
            data = response.json()

        logger.info("Inventory lookup for %s in %s: %s", sku_id, customer_city, data.get("fulfillment_options"))

        fulfillment_options = data.get("fulfillment_options", [])
        is_available = "OUT_OF_STOCK" not in fulfillment_options

        # Build human-readable message
        if "SHIP_HOME" in fulfillment_options:
            message = "✅ Available online — ships to your city in 2-5 days"
        elif "CLICK_COLLECT" in fulfillment_options:
            message = "✅ Available at your nearest store for same-day pickup"
        elif not is_available:
            message = "❌ This item is currently out of stock. I can suggest similar alternatives."
        else:
            message = f"✅ Available via {', '.join(fulfillment_options)}"

        return {
            "sku_id": sku_id,
            "availability": data,
            "fulfillment_options": fulfillment_options,
            "message": message,
            "is_available": is_available,
            "agent": "inventory",
        }

    except httpx.HTTPStatusError as e:
        logger.error("Inventory API HTTP error for %s: %s", sku_id, e)
        return {
            "sku_id": sku_id,
            "availability": {},
            "fulfillment_options": [],
            "message": f"❌ Could not check availability for {sku_id}. Error: {e.response.status_code}",
            "is_available": False,
            "agent": "inventory",
        }
    except Exception as e:
        logger.error("Inventory check failed for %s: %r", sku_id, e)
        return {
            "sku_id": sku_id,
            "availability": {},
            "fulfillment_options": [],
            "message": f"❌ Could not check availability right now. Please try again.",
            "is_available": False,
            "agent": "inventory",
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    test_input = {
        "sku_id": "SKU_001",
        "customer_city": "Mumbai",
    }

    print("\n" + "=" * 60)
    print("INVENTORY AGENT TEST")
    print("=" * 60)
    print(f"SKU: {test_input['sku_id']}")
    print(f"City: {test_input['customer_city']}")
    print("-" * 60)

    result = asyncio.run(run(test_input))

    print(f"\n✅ Agent: {result['agent']}")
    print(f"📦 SKU: {result['sku_id']}")
    print(f"📍 Available: {result['is_available']}")
    print(f"🚚 Fulfillment Options: {result['fulfillment_options']}")
    print(f"💬 Message: {result['message']}")
    print(f"\n📊 Raw Availability Data:")
    for key, val in result.get("availability", {}).items():
        if key != "all_locations":
            print(f"   {key}: {val}")

    print("\n" + "=" * 60)
    print("✅ Inventory agent test PASSED")
    print("=" * 60)
