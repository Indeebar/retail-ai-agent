"""
Loyalty Agent — applies loyalty perks and calculates final pricing.

Calls the loyalty mock API to get the customer's tier and active offers,
then calculates discounts and builds an itemized savings breakdown.
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
    Apply loyalty perks and calculate final pricing with all discounts.

    Input dict fields:
        customer_id: str
        cart: list — list of dicts with {sku_id, name, price, category, quantity}
        coupon_code: str (optional)

    Returns dict with original_total, final_total, total_savings,
    savings_breakdown, points_to_earn, agent.
    """
    customer_id: str = input.get("customer_id", "")
    cart: list = input.get("cart", [])
    coupon_code: str = input.get("coupon_code", None)

    try:
        async with httpx.AsyncClient(base_url=BACKEND_API_URL, timeout=10.0) as client:
            # 1. Get customer loyalty profile
            loyalty_resp = await client.get(f"/loyalty/{customer_id}")
            loyalty_resp.raise_for_status()
            loyalty_data = loyalty_resp.json()
            logger.info("Loyalty profile for %s: tier=%s", customer_id, loyalty_data.get("loyalty_tier"))

            # 2. Calculate discounts via POST /loyalty/calculate
            cart_items = [
                {
                    "sku_id": item.get("sku_id", ""),
                    "price": item.get("price", 0),
                    "category": item.get("category", ""),
                }
                for item in cart
            ]

            calc_payload = {
                "customer_id": customer_id,
                "cart_items": cart_items,
            }
            if coupon_code:
                calc_payload["coupon_code"] = coupon_code

            calc_resp = await client.post("/loyalty/calculate", json=calc_payload)
            calc_resp.raise_for_status()
            calc_data = calc_resp.json()
            logger.info("Loyalty calculation complete: subtotal=%.2f final=%.2f", calc_data.get("subtotal", 0), calc_data.get("final_price", 0))

        # 3. Build itemized savings breakdown string
        tier = loyalty_data.get("loyalty_tier", "Bronze")
        tier_discount = calc_data.get("tier_discount_amount", 0)
        coupon_discount = calc_data.get("coupon_discount_amount", 0)
        bundle_discount = calc_data.get("bundle_discount_amount", 0)
        total_discount = calc_data.get("total_discount", 0)

        breakdown_lines = []
        tier_emoji = {"Gold": "💛", "Silver": "🥈", "Bronze": "🥉"}.get(tier, "⭐")

        if tier_discount > 0:
            tier_rate = calc_data.get("savings_breakdown", {}).get("tier_discount", "")
            breakdown_lines.append(f"{tier_emoji} {tier} Member discount ({tier_rate}): -₹{tier_discount:.0f}")

        if coupon_discount > 0:
            breakdown_lines.append(f"🏷️ Coupon {coupon_code}: -₹{coupon_discount:.0f}")

        if bundle_discount > 0:
            bundles = calc_data.get("savings_breakdown", {}).get("bundles_applied", [])
            bundle_names = ", ".join(bundles) if bundles else "Bundle deal"
            breakdown_lines.append(f"🎁 {bundle_names}: -₹{bundle_discount:.0f}")

        if total_discount > 0:
            breakdown_lines.append(f"Total savings: ₹{total_discount:.0f}")
        else:
            breakdown_lines.append("No discounts applicable at this time.")

        savings_breakdown = "\n".join(breakdown_lines)

        return {
            "original_total": calc_data.get("subtotal", 0),
            "final_total": calc_data.get("final_price", 0),
            "total_savings": total_discount,
            "savings_breakdown": savings_breakdown,
            "points_to_earn": calc_data.get("points_to_earn", 0),
            "agent": "loyalty",
        }

    except httpx.HTTPStatusError as e:
        logger.error("Loyalty API HTTP error: %s — %s", e.response.status_code, e.response.text)
        return {
            "original_total": sum(item.get("price", 0) for item in cart),
            "final_total": sum(item.get("price", 0) for item in cart),
            "total_savings": 0,
            "savings_breakdown": "Could not calculate discounts at this time.",
            "points_to_earn": 0,
            "agent": "loyalty",
        }
    except Exception as e:
        logger.error("Loyalty agent failed: %r", e)
        return {
            "original_total": sum(item.get("price", 0) for item in cart),
            "final_total": sum(item.get("price", 0) for item in cart),
            "total_savings": 0,
            "savings_breakdown": "Could not calculate discounts at this time.",
            "points_to_earn": 0,
            "agent": "loyalty",
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    test_input = {
        "customer_id": "customer_001",
        "cart": [
            {"sku_id": "SKU_003", "name": "Kanjeevaram Silk Saree", "price": 1500, "category": "ethnic_wear", "quantity": 1},
            {"sku_id": "SKU_019", "name": "Embroidered Dupatta", "price": 1500, "category": "accessories", "quantity": 1},
        ],
        "coupon_code": None,
    }

    print("\n" + "=" * 60)
    print("LOYALTY AGENT TEST")
    print("=" * 60)
    print(f"Customer: {test_input['customer_id']}")
    print(f"Cart items: {len(test_input['cart'])}")
    print(f"Coupon: {test_input.get('coupon_code', 'None')}")
    print("-" * 60)

    result = asyncio.run(run(test_input))

    print(f"\n✅ Agent: {result['agent']}")
    print(f"💰 Original Total: ₹{result['original_total']}")
    print(f"🏷️ Total Savings: ₹{result['total_savings']}")
    print(f"💵 Final Total: ₹{result['final_total']}")
    print(f"⭐ Points to Earn: {result['points_to_earn']}")
    print(f"\n📋 Savings Breakdown:\n{result['savings_breakdown']}")

    print("\n" + "=" * 60)
    print("✅ Loyalty agent test PASSED")
    print("=" * 60)
