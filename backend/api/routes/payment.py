import logging
import random
import string

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class PaymentRequest(BaseModel):
    order_id: str
    method: str  # "saved_card" | "upi" | "gift_card" | "store_pos"
    amount: float
    customer_id: str


def _generate_txn_id() -> str:
    return "TXN_" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


def _suggest_method(current_method: str) -> str:
    if current_method == "saved_card":
        return "upi"
    if current_method == "upi":
        return "saved_card"
    return "upi"


@router.post("")
async def process_payment(req: PaymentRequest):
    """Simulate payment processing with random outcomes."""
    try:
        roll = random.random()

        if roll < 0.75:
            # SUCCESS
            txn_id = _generate_txn_id()
            result = {
                "status": "success",
                "transaction_id": txn_id,
                "message": f"Payment of INR {req.amount} processed successfully via {req.method}",
            }
        elif roll < 0.90:
            # DECLINED
            result = {
                "status": "declined",
                "transaction_id": None,
                "message": "Payment declined. Please try a different payment method.",
                "suggested_method": _suggest_method(req.method),
            }
        else:
            # RETRY_REQUIRED
            result = {
                "status": "retry",
                "transaction_id": None,
                "message": "Payment gateway timeout. Please retry.",
            }

        logger.info(
            "Payment attempt: order=%s method=%s amount=%.2f → %s",
            req.order_id,
            req.method,
            req.amount,
            result["status"],
        )
        return result

    except Exception as exc:
        logger.error("Payment processing error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
