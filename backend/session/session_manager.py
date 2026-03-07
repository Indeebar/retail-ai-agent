"""
Session Manager — Upstash Redis-backed session CRUD for cross-channel conversations.

Stores the full AgentState in Redis so that conversations persist
across turns and across channel switches (web → mobile → kiosk).
Each session has a 24-hour TTL.
"""

import json
import logging
import os
import sys
from pathlib import Path
from uuid import uuid4

# ── Ensure backend/ is on sys.path ──────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from upstash_redis import Redis

from graph.state import create_initial_state

logger = logging.getLogger(__name__)

SESSION_TTL = 86400  # 24 hours


# ═══════════════════════════════════════════════════════════════════════════
# REDIS CLIENT
# ═══════════════════════════════════════════════════════════════════════════

def get_redis_client() -> Redis:
    """
    Return an Upstash Redis client instance.

    Reads UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN
    from environment variables.

    Raises:
        ValueError: If the required environment variables are missing.
    """
    try:
        url = os.getenv("UPSTASH_REDIS_REST_URL")
        token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

        if not url or not token:
            raise ValueError(
                "UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN must be set"
            )

        client = Redis(url=url, token=token)
        logger.info("Upstash Redis client initialised: %s", url[:40])
        return client

    except Exception as e:
        logger.error("Failed to create Redis client: %r", e)
        raise


# ═══════════════════════════════════════════════════════════════════════════
# SESSION CRUD
# ═══════════════════════════════════════════════════════════════════════════

async def create_session(customer_id: str, channel: str) -> str:
    """
    Create a new session and store it in Redis.

    Args:
        customer_id: Customer profile ID (e.g. "customer_001").
        channel:     Interaction channel ("web", "mobile", "kiosk", "whatsapp").

    Returns:
        The newly generated session_id (e.g. "sess_a1b2c3d4e5f6").
    """
    session_id = "sess_" + uuid4().hex[:12]
    state = create_initial_state(session_id, customer_id, channel)

    redis = get_redis_client()
    redis.set(f"session:{session_id}", json.dumps(state), ex=SESSION_TTL)

    logger.info("Session created: %s (customer=%s, channel=%s)", session_id, customer_id, channel)
    return session_id


async def get_session(session_id: str) -> dict | None:
    """
    Load an existing session from Redis.

    Args:
        session_id: The session ID to look up.

    Returns:
        The parsed AgentState dict, or None if not found / expired.
    """
    redis = get_redis_client()
    data = redis.get(f"session:{session_id}")

    if data is None:
        logger.info("Session not found: %s", session_id)
        return None

    logger.info("Session loaded: %s", session_id)
    return json.loads(data)


async def save_session(session_id: str, state: dict) -> None:
    """
    Save an updated session state back to Redis.

    Resets the TTL to 24 hours on every save.

    Args:
        session_id: The session ID.
        state:      The full AgentState dict to persist.
    """
    redis = get_redis_client()
    redis.set(f"session:{session_id}", json.dumps(state), ex=SESSION_TTL)
    logger.info("Session saved: %s (%d messages)", session_id, len(state.get("messages", [])))


async def switch_channel(session_id: str, new_channel: str) -> dict | None:
    """
    Switch the channel for an existing session.

    Loads the session, updates the channel field, saves back to Redis,
    and returns the updated state.

    Args:
        session_id:  The session ID.
        new_channel: The new channel to switch to.

    Returns:
        The updated AgentState dict, or None if session not found.
    """
    state = await get_session(session_id)
    if state is None:
        logger.warning("Cannot switch channel — session %s not found", session_id)
        return None

    old_channel = state.get("channel", "unknown")
    state["channel"] = new_channel
    await save_session(session_id, state)

    logger.info("Session %s switched from %s to %s", session_id, old_channel, new_channel)
    return state


async def delete_session(session_id: str) -> None:
    """
    Delete a session from Redis.

    Args:
        session_id: The session ID to delete.
    """
    redis = get_redis_client()
    redis.delete(f"session:{session_id}")
    logger.info("Session deleted: %s", session_id)


# ═══════════════════════════════════════════════════════════════════════════
# __main__ — Quick smoke test
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import asyncio

    # Fix Windows encoding
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    async def test_session():
        print("\n" + "=" * 60)
        print("SESSION MANAGER TEST")
        print("=" * 60)

        # 1. Create session
        sid = await create_session("customer_001", "web")
        print(f"\n1. Created session: {sid}")

        # 2. Load session
        state = await get_session(sid)
        assert state is not None, "Session should exist"
        print(f"2. Loaded session: customer={state['customer_id']}, channel={state['channel']}")

        # 3. Update and save
        state["messages"].append({"role": "user", "content": "Hello!"})
        await save_session(sid, state)
        print(f"3. Saved session with {len(state['messages'])} message(s)")

        # 4. Switch channel
        updated = await switch_channel(sid, "mobile")
        assert updated is not None
        print(f"4. Switched channel: {updated['channel']}")

        # 5. Reload and verify
        reloaded = await get_session(sid)
        assert reloaded["channel"] == "mobile"
        assert len(reloaded["messages"]) == 1
        print(f"5. Reloaded: channel={reloaded['channel']}, messages={len(reloaded['messages'])}")

        # 6. Delete
        await delete_session(sid)
        gone = await get_session(sid)
        assert gone is None
        print("6. Deleted session — confirmed gone")

        print("\n" + "=" * 60)
        print("Session manager test PASSED")
        print("=" * 60)

    asyncio.run(test_session())
