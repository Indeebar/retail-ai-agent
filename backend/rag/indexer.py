"""
RAG Indexer — loads JSON data, embeds it, and indexes into Qdrant.
Idempotent: safe to call multiple times, skips already-indexed collections.
"""

import json
import time
import logging
from pathlib import Path

from rag.vectorstore import (
    get_client,
    ensure_collections_exist,
    upsert_vectors,
    collection_has_data,
    PRODUCTS_COLLECTION,
    HISTORY_COLLECTION,
    PROMOTIONS_COLLECTION,
)
from rag.embedder import (
    embed_batch,
    build_product_text,
    build_history_text,
    build_promotion_text,
)

logger = logging.getLogger(__name__)

# Path to data directory
DATA_DIR = Path(__file__).parent.parent / "data"


def index_products(client, force: bool = False) -> None:
    """
    Indexes product data into the products collection.
    Skips if already indexed unless force=True.
    """
    if not force and collection_has_data(client, PRODUCTS_COLLECTION):
        logger.info("Products already indexed, skipping")
        return

    logger.info("Indexing products...")
    with open(DATA_DIR / "products.json") as f:
        products = json.load(f)

    texts = [build_product_text(p) for p in products]
    vectors = embed_batch(texts)

    points = []
    for i, (product, vector) in enumerate(zip(products, vectors)):
        points.append({
            "id": i,
            "vector": vector,
            "payload": product,
        })

    upsert_vectors(client, PRODUCTS_COLLECTION, points)
    logger.info(f"Indexed {len(products)} products")


def index_customer_history(client, force: bool = False) -> None:
    """
    Indexes customer history into the customer_history collection.
    Skips if already indexed unless force=True.
    """
    if not force and collection_has_data(client, HISTORY_COLLECTION):
        logger.info("Customer history already indexed, skipping")
        return

    logger.info("Indexing customer history...")
    with open(DATA_DIR / "customers.json") as f:
        customers = json.load(f)

    texts = [build_history_text(c) for c in customers]
    vectors = embed_batch(texts)

    points = []
    for i, (customer, vector) in enumerate(zip(customers, vectors)):
        payload = {
            "id": customer["id"],
            "name": customer["name"],
            "loyaltyTier": customer["loyaltyTier"],
            "preferredCategories": customer["preferredCategories"],
            "purchaseHistory": [p["sku_id"] for p in customer.get("purchaseHistory", [])],
        }
        points.append({
            "id": i,
            "vector": vector,
            "payload": payload,
        })

    upsert_vectors(client, HISTORY_COLLECTION, points)
    logger.info(f"Indexed {len(customers)} customer profiles")


def index_promotions(client, force: bool = False) -> None:
    """
    Indexes all promotions (coupons, campaigns, bundles) into the promotions collection.
    Flattens all promotion types into a single list.
    Skips if already indexed unless force=True.
    """
    if not force and collection_has_data(client, PROMOTIONS_COLLECTION):
        logger.info("Promotions already indexed, skipping")
        return

    logger.info("Indexing promotions...")
    with open(DATA_DIR / "promotions.json") as f:
        promos_data = json.load(f)

    # Flatten all promotion types into a single list
    all_promos = []
    for coupon in promos_data.get("couponCodes", []):
        coupon["promoType"] = "coupon"
        all_promos.append(coupon)
    for campaign in promos_data.get("seasonalCampaigns", []):
        campaign["promoType"] = "campaign"
        all_promos.append(campaign)
    for bundle in promos_data.get("bundleDeals", []):
        bundle["promoType"] = "bundle"
        all_promos.append(bundle)

    texts = [build_promotion_text(p) for p in all_promos]
    vectors = embed_batch(texts)

    points = []
    for i, (promo, vector) in enumerate(zip(all_promos, vectors)):
        points.append({
            "id": i,
            "vector": vector,
            "payload": promo,
        })

    upsert_vectors(client, PROMOTIONS_COLLECTION, points)
    logger.info(f"Indexed {len(all_promos)} promotions")


def run_indexer(force: bool = False) -> None:
    """
    Main entry point for the RAG indexer.
    Connects to Qdrant, ensures collections exist, and indexes all data.
    Does NOT raise on error — the app should still start even if indexing fails.
    """
    start = time.time()
    try:
        client = get_client()
        ensure_collections_exist(client)

        index_products(client, force=force)
        index_customer_history(client, force=force)
        index_promotions(client, force=force)

        elapsed = round(time.time() - start, 2)
        logger.info(f"RAG indexing complete in {elapsed}s")
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        logger.error(f"RAG indexing failed after {elapsed}s: {e}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from dotenv import load_dotenv
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    run_indexer(force=True)
