"""
Text embedding using sentence-transformers.
Model is loaded ONCE at module level for performance.
"""

import logging
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Load model once at module level — critical for performance
logger.info("Loading sentence-transformers model: all-MiniLM-L6-v2...")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
logger.info("Sentence-transformers model loaded successfully.")

VECTOR_SIZE = 384


def embed_text(text: str) -> list[float]:
    """
    Embeds a single string and returns a Python list of floats.
    Returns a zero vector of length 384 for empty strings.
    """
    if not text or not text.strip():
        return [0.0] * VECTOR_SIZE
    embedding = model.encode(text)
    return embedding.tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """
    Embeds a list of strings in one batch call (faster than calling embed_text in a loop).
    Returns list of float lists.
    """
    logger.info(f"Embedding batch of {len(texts)} texts...")
    embeddings = model.encode(texts)
    return [e.tolist() for e in embeddings]


def build_product_text(product: dict) -> str:
    """
    Builds a single string from a product dict for embedding.
    Combines name, category, subcategory, occasion tags, and description.
    """
    name = product.get("name", "")
    category = product.get("category", "")
    occasions = ", ".join(product.get("occasionTags", []))
    description = product.get("description", "")
    return f"{name}. Category: {category}. Occasions: {occasions}. {description}"


def build_history_text(customer: dict) -> str:
    """
    Builds a descriptive string from a customer dict for embedding.
    Summarizes their preferences, purchase history, and loyalty tier.
    """
    name = customer.get("name", "")
    categories = ", ".join(customer.get("preferredCategories", []))
    sku_ids = ", ".join([p["sku_id"] for p in customer.get("purchaseHistory", [])])
    tier = customer.get("loyaltyTier", "")
    return f"Customer {name} prefers {categories}. Past purchases: {sku_ids}. Loyalty tier: {tier}."


def build_promotion_text(promo: dict) -> str:
    """
    Builds a descriptive string from a promotion dict for semantic retrieval.
    Handles coupons, seasonal campaigns, and bundle deals.
    """
    # Handle coupon codes
    if "code" in promo:
        code = promo.get("code", "")
        discount_type = promo.get("discountType", "")
        discount_value = promo.get("discountValue", "")
        min_order = promo.get("minOrderValue", 0)
        categories = ", ".join(promo.get("applicableCategories", []))
        expiry = promo.get("expiryDate", "")
        if discount_type == "percentage":
            discount_str = f"{int(discount_value * 100)}% off"
        else:
            discount_str = f"INR {discount_value} off"
        return f"Coupon {code}: {discount_str} on {categories}. Minimum order INR {min_order}. Valid until {expiry}."

    # Handle seasonal campaigns
    if "startDate" in promo:
        name = promo.get("name", "")
        discount_type = promo.get("discountType", "")
        discount_value = promo.get("discountValue", "")
        categories = ", ".join(promo.get("applicableCategories", []))
        start = promo.get("startDate", "")
        end = promo.get("endDate", "")
        if discount_type == "percentage":
            discount_str = f"{int(discount_value * 100)}% off"
        else:
            discount_str = f"INR {discount_value} off"
        return f"Campaign: {name}. {discount_str} on {categories}. From {start} to {end}."

    # Handle bundle deals
    if "requiredCategories" in promo:
        name = promo.get("name", "")
        categories = ", ".join(promo.get("requiredCategories", []))
        discount_type = promo.get("discountType", "")
        discount_value = promo.get("discountValue", "")
        if discount_type == "percentage":
            discount_str = f"{int(discount_value * 100)}% off"
        else:
            discount_str = f"INR {discount_value} off"
        return f"Bundle deal: {name}. Buy {categories} together and get {discount_str}."

    return str(promo)
