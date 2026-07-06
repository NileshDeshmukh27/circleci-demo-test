"""Demo handler for COS data pipeline."""

import logging

logger = logging.getLogger(__name__)


def process(event: dict) -> dict:
    """Process an incoming event and return status."""
    logger.info("Processing event: %s", event)
    return {"status": "ok", "input": event}
