import json
import logging
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@lru_cache(maxsize=1)
def _load_customers() -> list[dict]:
    with open(DATA_DIR / "customers.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_promotions() -> dict:
    with open(DATA_DIR / "promotions.json", encoding="utf-8") as f:
        return json.load(f)


def _find_customer(customer_id: str) -> Optional[dict]:
    for c in _load_customers():
        if c["id"] == customer_id:
            return c
    return None


def _active_coupons() -> list[dict]:
    """Return coupons that haven't expired yet."""
    today = date.today().isoformat()
    promos = _load_promotions()
    return [c for c in promos.get("couponCodes", []) if c.get("expiryDate", "") >= today]


def _applicable_campaigns() -> list[dict]:
    """Return seasonal campaigns where today falls between start and end."""
    today = date.today().isoformat()
    promos = _load_promotions()
    return [
        c for c in promos.get("seasonalCampaigns", [])
        if c.get("startDate", "") <= today <= c.get("endDate", "")
    ]


# ── GET /loyalty/{customer_id} ──────────────────────────────────────────────

@router.get("/{customer_id}")
async def get_loyalty(customer_id: str):
    """Get loyalty profile for a customer."""
    customer = _find_customer(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")

    promos = _load_promotions()
    tier = customer.get("loyaltyTier", "Bronze")

    return {
        "customer_id": customer_id,
        "loyalty_tier": tier,
        "loyalty_points": customer.get("loyaltyPoints", 0),
        "earn_rate": promos.get("loyaltyEarnRates", {}).get(tier, 1.0),
        "tier_discount": promos.get("tierDiscounts", {}).get(tier, 0),
        "active_coupons": _active_coupons(),
        "applicable_campaigns": _applicable_campaigns(),
    }


# ── POST /loyalty/calculate ─────────────────────────────────────────────────

class CartItem(BaseModel):
    sku_id: str
    price: float
    category: str


class CalculateRequest(BaseModel):
    customer_id: str
    cart_items: list[CartItem]
    coupon_code: Optional[str] = None


@router.post("/calculate")
async def calculate_loyalty(req: CalculateRequest):
    """Calculate tier discount, coupon discount, bundle discount, points earned, and final price."""
    customer = _find_customer(req.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer {req.customer_id} not found")

    promos = _load_promotions()
    tier = customer.get("loyaltyTier", "Bronze")
    tier_discount_rate = promos.get("tierDiscounts", {}).get(tier, 0)
    earn_rate = promos.get("loyaltyEarnRates", {}).get(tier, 1.0)

    subtotal = sum(item.price for item in req.cart_items)

    # 1. Tier discount
    tier_discount_amount = round(subtotal * tier_discount_rate, 2)

    # 2. Coupon discount
    coupon_discount_amount = 0.0
    if req.coupon_code:
        coupon = None
        for c in promos.get("couponCodes", []):
            if c["code"] == req.coupon_code:
                coupon = c
                break

        if not coupon:
            raise HTTPException(status_code=400, detail=f"Invalid coupon code: {req.coupon_code}")

        # Check expiry
        if coupon.get("expiryDate", "") < date.today().isoformat():
            raise HTTPException(status_code=400, detail=f"Coupon {req.coupon_code} has expired")

        # Check min order value
        if subtotal < coupon.get("minOrderValue", 0):
            raise HTTPException(
                status_code=400,
                detail=f"Minimum order value of {coupon['minOrderValue']} not met for coupon {req.coupon_code}",
            )

        # Apply coupon
        applicable_categories = coupon.get("applicableCategories", [])
        if "all" in applicable_categories:
            coupon_base = subtotal
        else:
            coupon_base = sum(item.price for item in req.cart_items if item.category in applicable_categories)

        if coupon["discountType"] == "percentage":
            coupon_discount_amount = round(coupon_base * coupon["discountValue"], 2)
        else:  # flat
            coupon_discount_amount = round(min(coupon["discountValue"], coupon_base), 2)

    # 3. Bundle discount
    bundle_discount_amount = 0.0
    cart_categories = set(item.category for item in req.cart_items)
    for bundle in promos.get("bundleDeals", []):
        required = set(bundle.get("requiredCategories", []))
        if required.issubset(cart_categories):
            applicable_items_total = sum(
                item.price for item in req.cart_items if item.category in required
            )
            bundle_discount_amount += round(applicable_items_total * bundle.get("discountValue", 0), 2)

    # 4. Final price
    total_discount = tier_discount_amount + coupon_discount_amount + bundle_discount_amount
    final_price = round(max(subtotal - total_discount, 0), 2)

    # 5. Points to earn
    points_to_earn = round(final_price * earn_rate)

    logger.info(
        "Loyalty calculation for %s: subtotal=%.2f tier_disc=%.2f coupon_disc=%.2f bundle_disc=%.2f final=%.2f points=%d",
        req.customer_id, subtotal, tier_discount_amount, coupon_discount_amount, bundle_discount_amount, final_price, points_to_earn,
    )

    return {
        "customer_id": req.customer_id,
        "loyalty_tier": tier,
        "subtotal": subtotal,
        "tier_discount_amount": tier_discount_amount,
        "coupon_discount_amount": coupon_discount_amount,
        "bundle_discount_amount": bundle_discount_amount,
        "total_discount": round(total_discount, 2),
        "final_price": final_price,
        "points_to_earn": points_to_earn,
        "savings_breakdown": {
            "tier_discount": f"{tier_discount_rate * 100:.0f}% ({tier} tier)",
            "coupon": req.coupon_code or "none",
            "bundles_applied": [
                b["name"] for b in promos.get("bundleDeals", [])
                if set(b.get("requiredCategories", [])).issubset(cart_categories)
            ],
        },
    }
