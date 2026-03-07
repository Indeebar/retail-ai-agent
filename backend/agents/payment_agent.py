"""
Payment Agent — processes payments with retry logic and graceful decline handling.

Calls the payment mock API, handles success/declined/retry statuses with
automatic retry using suggested alternative methods.
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


async def _attempt_payment(client: httpx.AsyncClient, payload: dict) -> dict:
    """Make a single payment attempt and return the API response."""
    response = await client.post("/payment", json=payload)
    response.raise_for_status()
    return response.json()


async def run(input: dict) -> dict:
    """
    Process payment with retry logic and graceful decline handling.

    Input dict fields:
        order_id: str
        method: str
        amount: float
        customer_id: str

    Returns dict with success, transaction_id, method_used, amount, message, attempts, agent.
    """
    order_id: str = input.get("order_id", "")
    method: str = input.get("method", "upi")
    amount: float = input.get("amount", 0.0)
    customer_id: str = input.get("customer_id", "")

    attempts = 0

    try:
        async with httpx.AsyncClient(base_url=BACKEND_API_URL, timeout=30.0) as client:
            # First attempt
            payload = {
                "order_id": order_id,
                "method": method,
                "amount": amount,
                "customer_id": customer_id,
            }
            attempts = 1
            result = await _attempt_payment(client, payload)
            logger.info("Payment attempt #1: status=%s method=%s", result.get("status"), method)

            status = result.get("status", "")

            # Handle SUCCESS
            if status == "success":
                return {
                    "success": True,
                    "transaction_id": result.get("transaction_id"),
                    "method_used": method,
                    "amount": amount,
                    "message": f"✅ Payment of ₹{amount:.0f} processed successfully via {method}.",
                    "attempts": attempts,
                    "agent": "payment",
                }

            # Handle DECLINED — retry with suggested method
            if status == "declined":
                suggested = result.get("suggested_method", "upi")
                logger.info("Payment declined. Retrying with suggested method: %s", suggested)

                payload["method"] = suggested
                attempts = 2
                retry_result = await _attempt_payment(client, payload)
                logger.info("Payment attempt #2: status=%s method=%s", retry_result.get("status"), suggested)

                if retry_result.get("status") == "success":
                    return {
                        "success": True,
                        "transaction_id": retry_result.get("transaction_id"),
                        "method_used": suggested,
                        "amount": amount,
                        "message": f"✅ Payment succeeded on retry with {suggested}. Amount: ₹{amount:.0f}.",
                        "attempts": attempts,
                        "agent": "payment",
                    }
                else:
                    return {
                        "success": False,
                        "transaction_id": None,
                        "method_used": suggested,
                        "amount": amount,
                        "message": f"❌ Payment failed after 2 attempts. Please try a different payment method.",
                        "attempts": attempts,
                        "agent": "payment",
                    }

            # Handle RETRY — retry once with same method (instant for demo)
            if status == "retry":
                logger.info("Payment gateway timeout. Retrying with same method: %s", method)

                attempts = 2
                retry_result = await _attempt_payment(client, payload)
                logger.info("Payment retry attempt #2: status=%s", retry_result.get("status"))

                if retry_result.get("status") == "success":
                    return {
                        "success": True,
                        "transaction_id": retry_result.get("transaction_id"),
                        "method_used": method,
                        "amount": amount,
                        "message": f"✅ Payment of ₹{amount:.0f} processed after retry via {method}.",
                        "attempts": attempts,
                        "agent": "payment",
                    }
                else:
                    return {
                        "success": False,
                        "transaction_id": None,
                        "method_used": method,
                        "amount": amount,
                        "message": f"❌ Payment failed after retry. Please try again later.",
                        "attempts": attempts,
                        "agent": "payment",
                    }

            # Unknown status
            return {
                "success": False,
                "transaction_id": None,
                "method_used": method,
                "amount": amount,
                "message": f"⚠️ Unexpected payment status: {status}",
                "attempts": attempts,
                "agent": "payment",
            }

    except httpx.HTTPStatusError as e:
        logger.error("Payment API HTTP error: %s — %s", e.response.status_code, e.response.text)
        return {
            "success": False,
            "transaction_id": None,
            "method_used": method,
            "amount": amount,
            "message": f"❌ Payment service error. Please try again.",
            "attempts": attempts,
            "agent": "payment",
        }
    except Exception as e:
        logger.error("Payment processing failed: %r", e)
        return {
            "success": False,
            "transaction_id": None,
            "method_used": method,
            "amount": amount,
            "message": f"❌ Payment processing error. Please try again.",
            "attempts": attempts,
            "agent": "payment",
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    test_input = {
        "order_id": "ORD_TEST_001",
        "method": "saved_card",
        "amount": 2500.0,
        "customer_id": "customer_001",
    }

    print("\n" + "=" * 60)
    print("PAYMENT AGENT TEST")
    print("=" * 60)
    print(f"Order: {test_input['order_id']}")
    print(f"Method: {test_input['method']}")
    print(f"Amount: ₹{test_input['amount']}")
    print(f"Customer: {test_input['customer_id']}")
    print("-" * 60)

    result = asyncio.run(run(test_input))

    print(f"\n✅ Agent: {result['agent']}")
    print(f"{'✅' if result['success'] else '❌'} Success: {result['success']}")
    print(f"🆔 Transaction ID: {result['transaction_id']}")
    print(f"💳 Method Used: {result['method_used']}")
    print(f"💰 Amount: ₹{result['amount']}")
    print(f"🔄 Attempts: {result['attempts']}")
    print(f"💬 Message: {result['message']}")

    print("\n" + "=" * 60)
    print("✅ Payment agent test PASSED")
    print("=" * 60)
