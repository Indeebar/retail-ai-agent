import logging
import random
import string
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class FulfillmentRequest(BaseModel):
    order_id: str
    fulfillment_type: str  # "SHIP_HOME" | "CLICK_COLLECT" | "IN_STORE"
    customer_id: str
    sku_ids: list[str]


def _generate_tracking_id() -> str:
    return "TRACK_" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


@router.post("")
async def process_fulfillment(req: FulfillmentRequest):
    """Process fulfillment for an order."""
    try:
        tracking_id = _generate_tracking_id()

        if req.fulfillment_type == "SHIP_HOME":
            eta_days = random.randint(2, 5)
            estimated_delivery = (date.today() + timedelta(days=eta_days)).isoformat()
            result = {
                "order_id": req.order_id,
                "fulfillment_type": req.fulfillment_type,
                "tracking_id": tracking_id,
                "estimated_delivery": estimated_delivery,
                "carrier": "BlueDart",
                "status": "confirmed",
                "sku_ids": req.sku_ids,
            }

        elif req.fulfillment_type == "CLICK_COLLECT":
            slot_time = "Tomorrow " + random.choice(["10:00 AM", "2:00 PM", "5:00 PM"])
            result = {
                "order_id": req.order_id,
                "fulfillment_type": req.fulfillment_type,
                "tracking_id": tracking_id,
                "pickup_slot": slot_time,
                "store": "nearest store",
                "status": "confirmed",
                "sku_ids": req.sku_ids,
            }

        elif req.fulfillment_type == "IN_STORE":
            result = {
                "order_id": req.order_id,
                "fulfillment_type": req.fulfillment_type,
                "tracking_id": tracking_id,
                "status": "reserved",
                "message": "Item reserved for 24 hours at your nearest store",
                "sku_ids": req.sku_ids,
            }

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid fulfillment type: {req.fulfillment_type}. Must be SHIP_HOME, CLICK_COLLECT, or IN_STORE.",
            )

        logger.info(
            "Fulfillment created: order=%s type=%s tracking=%s",
            req.order_id,
            req.fulfillment_type,
            tracking_id,
        )
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Fulfillment error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
