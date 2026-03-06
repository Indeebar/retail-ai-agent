import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter()

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

CITY_STORE_MAP = {
    "Mumbai": "store_mumbai",
    "Delhi": "store_delhi",
    "Bangalore": "store_bangalore",
}


@lru_cache(maxsize=1)
def _load_inventory() -> dict:
    with open(DATA_DIR / "inventory.json", encoding="utf-8") as f:
        return json.load(f)


@router.get("/{sku_id}")
async def get_inventory(
    sku_id: str,
    customer_city: Optional[str] = Query(None, description="Customer city for nearest store lookup"),
):
    """Return inventory + fulfillment options for a given SKU."""
    try:
        inventory = _load_inventory()

        if sku_id not in inventory:
            raise HTTPException(status_code=404, detail=f"SKU {sku_id} not found in inventory")

        sku_data = inventory[sku_id]
        online = sku_data.get("online_warehouse", {"quantity": 0, "in_stock": False})

        # Determine nearest store
        nearest_store_key = CITY_STORE_MAP.get(customer_city) if customer_city else None
        nearest_store_data = sku_data.get(nearest_store_key, {"quantity": 0, "in_stock": False}) if nearest_store_key else None

        # Build fulfillment options
        fulfillment_options = []
        if online.get("in_stock"):
            fulfillment_options.append("SHIP_HOME")
        if nearest_store_data and nearest_store_data.get("in_stock"):
            fulfillment_options.append("CLICK_COLLECT")
            fulfillment_options.append("IN_STORE")
        if not fulfillment_options:
            fulfillment_options.append("OUT_OF_STOCK")

        # Build response
        response = {
            "sku_id": sku_id,
            "online": {
                "quantity": online.get("quantity", 0),
                "in_stock": online.get("in_stock", False),
            },
            "nearest_store": {
                "location": nearest_store_key,
                "quantity": nearest_store_data.get("quantity", 0) if nearest_store_data else 0,
                "in_stock": nearest_store_data.get("in_stock", False) if nearest_store_data else False,
            } if nearest_store_key else None,
            "fulfillment_options": fulfillment_options,
            "all_locations": sku_data,
        }

        logger.info("Inventory lookup for %s (city=%s) → %s", sku_id, customer_city, fulfillment_options)
        return response

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error fetching inventory for %s: %s", sku_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
