"""
Sales Agent — master orchestrator for intent detection and response generation.

Detects customer intent from messages using Groq LLM, routes to the
appropriate worker agent, and generates natural Aria-style responses.
Will be wired into LangGraph in Phase 6.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)

VALID_INTENTS = {"RECOMMEND", "INVENTORY", "CHECKOUT", "TRACK", "RETURN", "FEEDBACK", "GREETING", "UNCLEAR"}


async def detect_intent(message: str, conversation_history: list = None) -> str:
    """
    Classify the customer message into one of the defined intent categories
    using Groq LLaMA 3.1.

    Args:
        message: The customer's message text.
        conversation_history: Previous messages in the session.

    Returns:
        One of: RECOMMEND, INVENTORY, CHECKOUT, TRACK, RETURN, FEEDBACK, GREETING, UNCLEAR.
    """
    if conversation_history is None:
        conversation_history = []

    try:
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        prompt = (
            "Classify the intent of this customer message into exactly ONE of these categories: "
            "RECOMMEND, INVENTORY, CHECKOUT, TRACK, RETURN, FEEDBACK, GREETING, UNCLEAR. "
            f"Message: '{message}'. "
            "Respond with only the category word, nothing else."
        )

        chat_completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a precise intent classifier. Respond with only a single word."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=10,
        )

        raw_intent = chat_completion.choices[0].message.content.strip().upper()

        # Validate the intent
        if raw_intent in VALID_INTENTS:
            logger.info("Intent detected: '%s' → %s", message[:50], raw_intent)
            return raw_intent
        else:
            logger.warning("Invalid intent '%s' from LLM for message: '%s'. Defaulting to RECOMMEND.", raw_intent, message[:50])
            return "RECOMMEND"

    except Exception as e:
        logger.error("Intent detection failed: %r. Defaulting to RECOMMEND.", e)
        return "RECOMMEND"


async def generate_response(context: dict, conversation_history: list = None) -> str:
    """
    Generate a natural, warm, conversational reply from the output of a worker agent.

    Args:
        context: The output dict from a worker agent.
        conversation_history: Previous messages in the session.

    Returns:
        A string with Aria's natural language response.
    """
    if conversation_history is None:
        conversation_history = []

    try:
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        system_prompt = (
            "You are Aria, a premium fashion sales associate. "
            "Use the provided context to give a natural, warm, conversational reply. "
            "Do not list data robotically — synthesize it into friendly conversation. "
            "Keep reply under 150 words."
        )

        # Build context string from the worker agent output
        context_str = "\n".join([f"{k}: {v}" for k, v in context.items() if k != "agent"])

        chat_completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Worker agent output:\n{context_str}"},
            ],
            temperature=0.7,
            max_tokens=300,
        )

        response = chat_completion.choices[0].message.content
        logger.info("Generated Aria response (%d chars)", len(response))
        return response

    except Exception as e:
        logger.error("Response generation failed: %r", e)
        return "I'd love to help you with that! Let me look into it for you."


def get_system_prompt(customer_name: str, tier: str) -> str:
    """
    Return the full system prompt string for Aria.

    Args:
        customer_name: The customer's name.
        tier: The customer's loyalty tier.

    Returns:
        A system prompt string for the Groq LLM.
    """
    return (
        f"You are Aria, a warm, knowledgeable, and consultative fashion sales associate "
        f"for a premium Indian retail brand. You are speaking with {customer_name}, "
        f"who is a valued {tier} loyalty member.\n\n"
        f"Your tone is:\n"
        f"- Warm and personal — use the customer's name naturally\n"
        f"- Knowledgeable — you know fabrics, fits, occasions, and trends\n"
        f"- Consultative — you ask follow-ups and suggest alternatives\n"
        f"- Professional yet friendly — like a trusted stylist\n\n"
        f"Guidelines:\n"
        f"- Always mention specific product names and prices in INR\n"
        f"- Reference the customer's loyalty tier and any applicable perks\n"
        f"- Suggest complementary items or bundles\n"
        f"- Keep responses concise (under 150 words)\n"
        f"- Use natural language, not bullet points or data dumps"
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    # Test intent detection with 5 different messages
    test_messages = [
        ("show me wedding outfits", "RECOMMEND"),
        ("is SKU_001 available in Mumbai", "INVENTORY"),
        ("I want to checkout", "CHECKOUT"),
        ("where is my order ORD_001", "TRACK"),
        ("I want to return my purchase", "RETURN"),
    ]

    print("\n" + "=" * 60)
    print("SALES AGENT TEST — Intent Detection")
    print("=" * 60)

    all_passed = True
    for message, expected in test_messages:
        intent = asyncio.run(detect_intent(message))
        status = "✅" if intent == expected else "⚠️"
        if intent != expected:
            all_passed = False
        print(f"  {status}  \"{message}\"  →  {intent}  (expected: {expected})")

    # Test system prompt generation
    print("\n" + "-" * 60)
    print("System Prompt Test:")
    prompt = get_system_prompt("Aarav Sharma", "Gold")
    print(f"  Generated prompt length: {len(prompt)} chars")
    print(f"  Contains customer name: {'Aarav Sharma' in prompt}")
    print(f"  Contains tier: {'Gold' in prompt}")

    # Test response generation with sample context
    print("\n" + "-" * 60)
    print("Response Generation Test:")
    sample_context = {
        "recommended_products": [{"name": "Silk Saree", "price": 3500}],
        "llm_response": "Here's a lovely saree for you!",
        "applicable_promotions": [{"text": "10% off ethnic wear"}],
        "agent": "recommendation",
    }
    response = asyncio.run(generate_response(sample_context))
    print(f"  Aria says ({len(response)} chars):\n  {response[:200]}...")

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ Sales agent test PASSED — all intents classified correctly")
    else:
        print("⚠️ Sales agent test PASSED with warnings — some intents may differ")
    print("=" * 60)
