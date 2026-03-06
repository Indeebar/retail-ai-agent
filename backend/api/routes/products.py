import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter()

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@lru_cache(maxsize=1)
def _load_products() -> list[dict]:
    with open(DATA_DIR / "products.json", encoding="utf-8") as f:
        return json.load(f)


@router.get("")
async def get_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    occasion: Optional[str] = Query(None, description="Filter by occasion tag"),
    max_price: Optional[int] = Query(None, description="Maximum price"),
    min_price: Optional[int] = Query(None, description="Minimum price"),
):
    """Return products, optionally filtered by category, occasion, price range."""
    try:
        products = list(_load_products())  # shallow copy

        if category:
            products = [p for p in products if p.get("category") == category]
            logger.info("Filtered by category=%s → %d products", category, len(products))

        if occasion:
            products = [p for p in products if occasion in p.get("occasionTags", [])]
            logger.info("Filtered by occasion=%s → %d products", occasion, len(products))

        if min_price is not None:
            products = [p for p in products if p.get("price", 0) >= min_price]
            logger.info("Filtered by min_price=%d → %d products", min_price, len(products))

        if max_price is not None:
            products = [p for p in products if p.get("price", 0) <= max_price]
            logger.info("Filtered by max_price=%d → %d products", max_price, len(products))

        return {"products": products, "count": len(products)}

    except Exception as exc:
        logger.error("Error fetching products: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
