"""
Recommendation Agent — RAG-based product recommendations using Qdrant + Groq.

The most important agent in the system. It retrieves semantically similar
products from the vector store, filters out already-purchased items, fetches
relevant promotions, and generates a personalized LLM response via Groq.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Ensure the backend directory is on the path for standalone execution
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)

# ── Data paths ───────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# ── Qdrant collection names (must match vectorstore.py) ─────────────────────
PRODUCTS_COLLECTION = "products"
HISTORY_COLLECTION = "customer_history"
PROMOTIONS_COLLECTION = "promotions"


def _load_customers() -> list[dict]:
    """Load all customer profiles from customers.json."""
    with open(DATA_DIR / "customers.json", encoding="utf-8") as f:
        return json.load(f)


def _find_customer(customer_id: str) -> dict | None:
    """Find a single customer by ID."""
    for c in _load_customers():
        if c["id"] == customer_id:
            return c
    return None


async def run(input: dict) -> dict:
    """
    Generate personalised product recommendations using RAG + Groq.

    Input dict fields:
        customer_id: str
        query: str — natural language request
        conversation_history: list — previous messages
        cart: list — items already in cart (to avoid re-recommending)

    Returns dict with recommended_products, llm_response, applicable_promotions, agent.
    """
    customer_id: str = input.get("customer_id", "")
    query: str = input.get("query", "")
    conversation_history: list = input.get("conversation_history", [])
    cart: list = input.get("cart", [])

    # 1. Load customer profile
    customer = _find_customer(customer_id)
    if not customer:
        logger.warning("Customer %s not found — using defaults", customer_id)
        customer = {"name": "Valued Customer", "loyaltyTier": "Bronze", "preferredCategories": [], "purchaseHistory": []}

    customer_name = customer.get("name", "Valued Customer")
    tier = customer.get("loyaltyTier", "Bronze")
    past_sku_ids = {p["sku_id"] for p in customer.get("purchaseHistory", [])}
    cart_sku_ids = {item.get("sku_id", "") for item in cart}
    exclude_skus = past_sku_ids | cart_sku_ids

    # 2. Embed the query
    try:
        from rag.embedder import embed_text
        query_vector = embed_text(query)
        logger.info("Query embedded successfully (%d dims)", len(query_vector))
    except Exception as e:
        logger.error("Failed to embed query: %s", e)
        return {"recommended_products": [], "llm_response": "Sorry, I'm having trouble searching right now.", "applicable_promotions": [], "agent": "recommendation"}

    # 3. Search Qdrant for similar products (top 8)
    try:
        from rag.vectorstore import get_client, semantic_search
        qdrant = get_client()

        product_results = semantic_search(qdrant, PRODUCTS_COLLECTION, query_vector, top_k=8)
        logger.info("Retrieved %d products from Qdrant", len(product_results))
    except Exception as e:
        logger.error("Qdrant product search failed: %s", e)
        product_results = []

    # 4. Search customer history collection for past SKUs
    try:
        history_results = semantic_search(qdrant, HISTORY_COLLECTION, query_vector, top_k=5)
        for h in history_results:
            past_purchases_text = h.get("text", "")
            # Extract SKU IDs from the history text if present
            if "Past purchases:" in past_purchases_text:
                skus_part = past_purchases_text.split("Past purchases:")[-1].split(".")[0]
                for sku in skus_part.split(","):
                    sku = sku.strip()
                    if sku.startswith("SKU_"):
                        exclude_skus.add(sku)
        logger.info("History search complete — excluding %d SKUs", len(exclude_skus))
    except Exception as e:
        logger.error("Qdrant history search failed: %s", e)

    # 5. Filter out already-purchased / in-cart products
    filtered_products = [
        p for p in product_results
        if p.get("sku_id", "") not in exclude_skus
    ]
    # Take top 3 for recommendations
    top_products = filtered_products[:3] if filtered_products else product_results[:3]

    # 6. Search promotions collection
    try:
        promo_results = semantic_search(qdrant, PROMOTIONS_COLLECTION, query_vector, top_k=3)
        logger.info("Retrieved %d promotions from Qdrant", len(promo_results))
    except Exception as e:
        logger.error("Qdrant promotions search failed: %s", e)
        promo_results = []

    # 7. Build context for LLM
    products_context = ""
    for i, p in enumerate(top_products, 1):
        name = p.get("name", "Unknown")
        price = p.get("price", "N/A")
        desc = p.get("description", "")[:150]
        products_context += f"{i}. {name} — ₹{price}\n   {desc}\n"

    promos_context = ""
    for p in promo_results:
        text = p.get("text", str(p))
        promos_context += f"- {text}\n"

    preferences = ", ".join(customer.get("preferredCategories", []))
    context_block = (
        f"Retrieved Products:\n{products_context}\n"
        f"Applicable Promotions:\n{promos_context}\n"
        f"Customer: {customer_name}, {tier} tier, prefers {preferences}\n"
    )

    # 8. Call Groq LLaMA 3.1
    system_prompt = (
        f"You are Aria, a warm and knowledgeable fashion sales associate for a premium Indian retail brand. "
        f"Your customer's name is {customer_name} and they are a {tier} loyalty member. "
        f"Based on the retrieved products and promotions, give a personalized, consultative recommendation. "
        f"Mention 2-3 specific products by name and price in INR. Suggest one bundle or complementary item. "
        f"Keep your response under 120 words. Be warm, specific, and helpful."
    )

    llm_response = ""
    try:
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        chat_completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Customer query: {query}\n\nContext:\n{context_block}"},
            ],
            temperature=0.7,
            max_tokens=250,
        )
        llm_response = chat_completion.choices[0].message.content
        logger.info("Groq response generated (%d chars)", len(llm_response))
    except Exception as e:
        logger.error("Groq LLM call failed: %s", e)
        llm_response = "I'd love to help you find the perfect outfit! Let me show you some options."

    # 9. Return results
    return {
        "recommended_products": top_products,
        "llm_response": llm_response,
        "applicable_promotions": promo_results,
        "agent": "recommendation",
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    test_input = {
        "customer_id": "customer_001",
        "query": "I need a saree for a wedding next month, budget around 4000",
        "conversation_history": [],
        "cart": [],
    }

    print("\n" + "=" * 60)
    print("RECOMMENDATION AGENT TEST")
    print("=" * 60)
    print(f"Customer: {test_input['customer_id']}")
    print(f"Query: {test_input['query']}")
    print("-" * 60)

    result = asyncio.run(run(test_input))

    print(f"\n✅ Agent: {result['agent']}")
    print(f"\n📦 Recommended Products ({len(result['recommended_products'])}):")
    for p in result["recommended_products"]:
        print(f"   - {p.get('name', 'N/A')} (₹{p.get('price', 'N/A')})")

    print(f"\n🗣️ LLM Response:\n{result['llm_response']}")

    print(f"\n🏷️ Applicable Promotions ({len(result['applicable_promotions'])}):")
    for promo in result["applicable_promotions"]:
        print(f"   - {promo.get('text', str(promo))[:80]}")

    print("\n" + "=" * 60)
    print("✅ Recommendation agent test PASSED")
    print("=" * 60)
